import cPickle
import numpy as np
from .bleu import Bleu

def search_line(pss,bleus, weights, feature_id):
    '''
    return new_weights(change only ith weight) and new best bleu
    '''
    break_points = [] # num_sentence * num_break_points
    belongs = [] # num_sentence * (num_break_points + 1)
    n = len(pss)
    # calculate break-points
    for i in xrange(n):
        ps = pss[i]
        ps_np = np.asarray(ps)
        weights_np = np.array([weights])
        break_point, belong = search_break_points(ps_np, weights_np, feature_id)
        break_points.append(break_point)
        belongs.append(belong)

    new_weight, best_bleu_score = combine_break_points(break_points,belongs,bleus)
    
    new_weights = list(weights)
    new_weights[feature_id] = new_weight

    return new_weights, best_bleu_score


def combine_break_points(break_points, belongs, bleus, debug = False):
    '''Combine those break_points

    return new ith weight, new best bleu
    '''
    all_break_points = []

    for sen_id in xrange(len(break_points)):
        bps = break_points[sen_id]
        bps_zip = [(x,sen_id,i) for i,x in enumerate(bps)] # [(break_point, sentence_id, break_point_id)]
        all_break_points += bps_zip
    
    all_break_points = sorted(all_break_points)

    
    # combine all the break points
    bps = [] # store all the merges break-points
    bls = [] # store the corpus bleu score for each interval
    i = 0 
    thres = 0.001
    while i< len(all_break_points):
        v,sid,sbpid = all_break_points[i]
        bp = BP(v,sid,sbpid)
        i+=1
        while i< len(all_break_points):
            new_v,sid,sbpid = all_break_points[i]
            if abs(new_v-v) < thres:
                bp.add(sid,sbpid)
                i+=1
            else:
                break
        bps.append(bp)

    # calculate the blue using top-1
    if debug:
        b = Bleu()
        for bleu in bleus:
            b.add_bleu(bleu[0])
        print b.get_bleu()


    # calculate bleu along bps

    b = Bleu()
    current_belong = [] # 
    # calculate the first bleu score
    for i in xrange(len(bleus)):
        bleu_array = bleus[i]
        belong = belongs[i]
        top_id = belong[0]
        current_belong.append(top_id)
        bleu_object = bleu_array[top_id]
        b.add_bleu(bleu_object)

    bleu_0 = b.get_bleu()
    bls.append(bleu_0)
    
    for i in xrange(len(bps)):
        change_list = bps[i].sub_bps
        for sid, belong_id in change_list:
            # remove
            to_remove_sbpid = current_belong[sid]
            b.minus_bleu(bleus[sid][to_remove_sbpid])

            # add
            to_add_sbpid = belongs[sid][belong_id+1]
            b.add_bleu(bleus[sid][to_add_sbpid])
            current_belong[sid] = to_add_sbpid

        bleu_i = b.get_bleu()
        #print b.precision, b.length, b.ref_length
        bls.append(bleu_i)
        if debug:
            print bleu_i, bps[i], current_belong

    # search for the best interval
    new_weight = None
    best_bleu_score = 0.0
    best_bleu_id = 0
    min_zero_distance = float('inf')

    for i, bl in enumerate(bls):

        if best_bleu_score < bl:
            best_bleu_score = bl
            best_bleu_id = i
            min_zero_distance = float('inf')
        elif best_bleu_score == bl:
            bps_id = i
            if bps_id == len(bps):
                bps_id -= 1
            zero_distance = abs(bps[bps_id].bp)
            if min_zero_distance >= zero_distance:
                min_zero_distance == zero_distance
                best_bleu_id = i
    
    if best_bleu_id == 0 :
        new_weight = bps[0].bp
    elif best_bleu_id == len(bls)-1:
        new_weight = bps[best_bleu_id-1].bp
    else:
        new_weight = (bps[best_bleu_id-1].bp + bps[best_bleu_id].bp) *1.0 / 2
        
    
    return new_weight, best_bleu_score




def search_break_points(partial_scores,feature_values,feature_id):
    '''
    partial_scores, feature_values, should be a 2D np.array
    '''
    feature = partial_scores[:,feature_id]
    b = np.dot(partial_scores,feature_values.T)[:,0]
    b = b-feature * feature_values[0][feature_id] # 1 d
    
    lines = [(i,feature[i],b[i]) for i in xrange(len(partial_scores))] 
    lines = sorted(lines, key = lambda x: (x[1],-x[2])) # sort according to slope of target weight (the target feature value)

    # search break points
    break_points = []
    belongs = []
    current = 0
    belongs.append(lines[0][0])
    while True:
        left_most = float('inf')
        belong = -1
        a1 = lines[current][1]
        b1 = lines[current][2]
        next_id = -1
        for i in xrange(current+1,len(lines)):
            a2 = lines[i][1]
            b2 = lines[i][2]
            if a1 == a2:
                continue
            break_point = (b2-b1)/(a1-a2)
            if break_point < left_most:
                left_most = break_point
                belong = lines[i][0]
                next_id = i
        if belong != -1:
            break_points.append(left_most)
            belongs.append(belong)
        current = next_id
        if current == -1 or current == len(lines)-1:
            break
    
    if len(break_points) == 0:
        break_points.append(0)
        belongs.append(lines[0][0])

    return break_points, belongs
    

class BP:
    def __init__(self,bp,sid,sbpid):
        self.bp = bp
        self.sub_bps = [(sid,sbpid),] # [(sentence_id, sub_break_point_id)]
    
    def add(self, sid,sbpid):
        self.sub_bps.append((sid,sbpid))

    def __repr__(self):
        s = repr(self.bp) +' '+repr(self.sub_bps)
        return s
# ==== Test ====

def test_search_line():
    weights = [0.2,0.2,0.2,0.2,0.1,0.1,0.5,0.3]
    #weights =[-0.2602263480656042, -1.5631196861061967, -0.22872336139641586, -0.3835543710169499, 3.6099745577140219, 0.1, 0.5, 0.3]
    pss,tss,bleus = cPickle.load(open('/Users/xingshi/Workspace/misc/pyPBMT/var/v1/ptbs.pickle'))
    i = 5
    new_weights, best_bleu_score = search_line(pss,bleus,weights,i)
    print new_weights
    print best_bleu_score

def test_search_break_points():
    #ps,ts = cPickle.load(open('/Users/xingshi/Workspace/misc/pyPBMT/var/pts.pickle'))
    pss,tss,bleus = cPickle.load(open('/Users/xingshi/Workspace/misc/pyPBMT/var/v1/ptbs.pickle'))
    ps = pss[0]
    ps = np.array(ps)
    feature_values = np.array([[0.2,0.2,0.2,0.2,0.1,0.1,0.5,0.3]])
    bps,bls = search_break_points(ps,feature_values,5)
    print bps
    print bls

if __name__ == '__main__':
    test_search_line()
    test_search_break_points()
