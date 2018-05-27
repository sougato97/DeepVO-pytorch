from params import params
from data_manager import prepare_sequence_data
from model import DeepVO
import numpy as np
from PIL import Image
import glob
import os
import time
import torch
import torch.utils.data as Data

#use_pad = (params.seq_len[0] != params.seq_len[1])

# Model
M_deepvo = DeepVO(params.img_h, params.img_w)
M_deepvo.load_state_dict(torch.load(params.load_model_path))
print('Load model from: ', params.load_model_path)

M_deepvo.eval()

use_cuda = torch.cuda.is_available()
if use_cuda:
    M_deepvo = M_deepvo.cuda()
'''
video = '04'
testdata_path = 'KITTI/segmented_image/04_seq_8_8_im_184_608'
if os.path.isfile(testdata_path):
    data = np.load(testdata_path)
    X, Y = data['x'], data['y']
else:
    X, Y = prepare_sequence_data([video], params.seq_len, 'single', overlap=1, sample_interval=None)

print('X: ', X.shape)
print('Y: ', Y.shape)

# Preprocess, X subtract by the mean RGB values of training set
for c in range(3):
    mean = params.RGB_means[c]
    X[:,:,c] -= mean
'''
video = '04'
fnames = glob.glob('KITTI/images/{}/*.png'.format(video))  #unorderd
fnames.sort()
Y = np.load('KITTI/pose_GT/{}.npy'.format(video))
x_seq = []

seq_len = params.seq_len[0]
has_predict = False
answer = [None, ]
for i, fn in enumerate(fnames):
    im = Image.open(fn)
    if im.size != (params.img_w, params.img_h):
        im = im.resize((params.img_w, params.img_h), Image.ANTIALIAS)
    im = np.array(im)  #, dtype=float)  # (h, w, c)
    im = np.rollaxis(im, 2, 0)  #(c, h, w)
    im = np.expand_dims(im, axis=0)  #(1, c, h, w)
    
    #x_seq = im if x_seq == [] else np.concatenate((x_seq, im), axis=0)
    assert(len(x_seq) <= seq_len)
    if x_seq == []:
        x_seq = im
    else:
        if not has_predict:
            x_seq = np.concatenate((x_seq, im), axis=0)
        else:
            x_seq[:-1] = x_seq[1:]
            x_seq[-1] = im

        if len(x_seq) == seq_len:
            # Predict
            x = torch.from_numpy(np.expand_dims(x_seq, axis=0))
            x = x.type(torch.FloatTensor)
            # preprocess, subtrac by RGB mean
            for c in range(3):
                x[:,:,c] -= params.RGB_means[c]

            if use_cuda:
                x = x.cuda()

            predict = M_deepvo.forward(x)
            predict = predict.data.cpu().numpy()[0]  # only 1 in batch
            if not has_predict:
                for pose in predict:
                    answer.append([float(v) for v in pose])
                has_predict = True
            else:
                answer.append([float(v) for v in predict[-1]])  #if i >= seq_len-1
            x_seq[:-1] = x_seq[1:]
        print(answer[-1])
        

print('len(answer): ', len(answer)-1)
print('expect len: ', len(fnames)-1)

save_dir = 'result/'
if not os.path.exists(save_dir):
    os.makedirs(save_dir)
with open('{}out_{}.txt'.format(save_dir, video), 'w') as f:
    for pose in answer:
        if type(pose) == list:
            f.write(', '.join([str(p) for p in pose]))
        else:
            f.write(str(pose))
        f.write('\n')