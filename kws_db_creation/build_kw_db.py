'''
Builds keyword database after running force alignment on audio files
'''

import os
import json
from scipy.io import wavfile
from joblib import Parallel, delayed
from tqdm import tqdm
from collections import Counter
import pandas as pd
import random


def get_offset(path2transcription):
    """
    Get the moment in the audio file where the TED speaker starts talking

    Args:
    path2transcription: File path of the transcription (.stm file).

    Returns:
    Float, the offset value.
    """
    with open(path2transcription, 'rt') as f:
        records = f.readlines()
        for sentence in records:
            fields = sentence.split()
            label = fields[6:]
            if not 'ignore_time_segment_in_scoring' in label:
                return float(fields[3])
    return


def get_jsons(path='/aimlx/Datasets/TEDLIUM_release1/dev/json'):
    """
    Get the paths of the json files containing the forced alignement's key informations

    Args:
    path: Path to folder which contains the json files

    Returns:
    List, paths to json files.
    """ 
    path2jsons = []
    for _, _, files in os.walk(path):
        for file in files:
            if file.endswith('.json') and 'checkpoint' not in file:
                path2jsons.append(os.path.join(path, file))    
                
    return path2jsons

def extract_kw_dev_test(keyword, path2jsons, path2kw_db='/aimlx/Datasets/TEDLIUM_release1/eval_set', padding=True, win_size=1.0):
    """
    Aligning the keyword with the audio files, extracting and saving it as a new .wav file in path2kw_db/keyword/{speaker_name}_{i}.wav. 
    The naming convention is {speaker_name}_{i}, where i is the occurence index of the keyword in the transcription.
    This function is designed for the test and dev set of TEDLIUM.
    
    Args:
    keyword: desired keyword to be extracted
    path2jsons: list of json files containing the forced alignement's key informations
    path2kw_db: path where to save the extracted keywords
    padding: pad keywords with actual speech to have fixed length keywords
    win_size: window size of centered around the keyword
    
    """ 
    print('Extracting keyword {kw} from dev and test audio files'.format(kw=keyword))

    if not os.path.exists(os.path.join(path2kw_db, keyword[0])):
        os.mkdir(os.path.join(path2kw_db, keyword[0]))    

    path2wav = os.path.join(path2kw_db, keyword[0], keyword)
        
    if not os.path.exists(os.path.join(path2wav)):
        os.mkdir(os.path.join(path2wav))
        
    for path in tqdm(path2jsons):
        with open(path) as json_file:
            data = json.load(json_file)
            count = 0
            for word in data['words']:
                if word['word'] == keyword and word['case'] == 'success':
                    start, end = word['start'], word['end']
                    offset = get_offset(path2transcription=path.replace('.json', '.stm').replace('final_json', 'stm'))
                    fs, signal = wavfile.read(path.replace('.json', '.wav').replace('final_json', 'wav'))
                    
                    if padding:
                        for i, spot in enumerate(['beg', 'mid', 'end']):
                            start_w, end_w = extract_padded_kw(start+offset, end+offset, fs, win_size=win_size, kw_spot=spot)
                            end_w = min(end_w, len(signal))
                            filename = path.split('/')[-1].split('.')[0] + '_' + str(count) + '*' + str(i) + '.wav'
                            wavfile.write(os.path.join(path2wav, filename), data=signal[start_w:end_w], rate=fs)
                    else:
                        start, end = int(fs * (start + offset)), int(fs * (end + offset)) 
                        filename = path.split('/')[-1].split('.')[0] + '_' + str(count) + '.wav'
                        wavfile.write(os.path.join(path2wav, filename), data=signal[start:end], rate=fs)
                    count += 1 
                    
def extract_kw_train(keyword, path2jsons, path2kw_db='/aimlx/Datasets/TEDLIUM_release-3/data/1000_kws_db', padding=True, win_size=1.0):
    """
    This function is designed for the train set of TEDLIUM.

    Aligning the keyword with the audio files, extracting and saving it as a new .wav file in path2kw_db/keyword/{speaker_name}_{i}.wav. 
    The naming convention is {speaker_name}_{i}, where i is the occurence index of the keyword in the transcription.
    
    Args:
    keyword: desired keyword to be extracted
    path2jsons: list of json files containing the forced alignement's key informations
    path2kw_db: path where to save the extracted keywords
    padding: pad keywords with actual speech to have fixed length keywords
    win_size: window size of centered around the keyword

    
    """ 
    print('Extracting keyword {kw} from train audio files'.format(kw=keyword))
    
    if not os.path.exists(os.path.join(path2kw_db, keyword[0])):
        os.mkdir(os.path.join(path2kw_db, keyword[0]))
     
    path2wav = os.path.join(path2kw_db, keyword[0], keyword)

    if not os.path.exists(os.path.join(path2wav)):
        os.mkdir(os.path.join(path2wav))
    
    for path in tqdm(path2jsons):
        with open(path) as json_file:
            data = json.load(json_file)
            count = 0
            for word_id in data['words']:
                word = data['words'][word_id]
                if word['word'] == keyword and word['case'] == 'success':
                    start, end = word['start'], word['end']
                    
                    path = path.replace('.json', '.wav')
                    path = path.replace('final_json', 'wav')
                    fs, signal = wavfile.read(path)
                    
                    if padding:
                        #for i, spot in enumerate(['beg', 'mid', 'end']):
                        spot = random.sample(['beg', 'mid', 'end'], k=1)[0]
                        
                        start_w, end_w = extract_padded_kw(start, end, fs, win_size=win_size, kw_spot=spot)
                        end_w = min(end_w, len(signal))
                        #filename = path.split('/')[-1].split('.')[0] + '_' + str(count) + '*' + str(i) + '.wav'
                        filename = path.split('/')[-1].split('.')[0] + '_' + str(count) + '.wav'
                        wavfile.write(os.path.join(path2wav, filename), data=signal[start_w:end_w], rate=fs)
                    else:
                        start, end = int(fs * start), int(fs * end)
                        filename = path.split('/')[-1].split('.')[0] + '_' + str(count) + '.wav'
                        wavfile.write(os.path.join(path2wav, filename), data=signal[start:end], rate=fs)
                    count += 1 


def word_count(path2jsons, output):
    """
    Create a dictionary with words frequencies for either the dev, test or train set. 
    
    Args:
    path2jsons: list of json files containing the forced alignement's key informations
    output: path where result is saved (as a json file)
    """
    
    word_count = Counter({})
    
    for path in tqdm(path2jsons):
        with open(path) as json_file:
            data = json.load(json_file)
            word_dict = dict(pd.Series(data['transcript'].split()).value_counts())
            word_dict = {k: float(v) for k, v in word_dict.items()}
            word_count = word_count + Counter(word_dict)
    
    word_count = dict(word_count)
    with open(output, 'w') as fp:
        json.dump(word_count, fp)
        

def overall_word_count(path2wordcounts, save_result=False):
    """
    Create dictionary of overall words frequencies in tedlium's first release.
    
    Args:
    path2wordcounts: list with the path to the three json files with words counts of the dev, test and train set
    save_result: bool, whether results are saved as a json file in working directory or returned
    
    Returns:
    result: overall words frequencies in tedlium's first release.
    """
    
    result = Counter({})
    for path in path2wordcounts:
        with open(path) as json_file:
            data = json.load(json_file)
            result = result + Counter(data)
    
    if save_result:
        with open(os.path.join(os.getcwd(),'overall_word_count.json'), 'w') as fp:
            json.dump(result, fp)
    else:
        return result


def extract_padded_kw(start, end, fs, win_size=1.0, kw_spot='mid'):
    kw_dur = end - start
    if kw_dur > win_size:
        end = start + win_size
    else:
        speech_dur = win_size - kw_dur 
        if kw_spot == 'beg':
            rnd = random.uniform(0, 0.25*speech_dur)
            start = start - rnd
            end = end + (speech_dur - rnd)            
        elif kw_spot == 'mid':
            rnd = random.uniform(speech_dur*0.25, speech_dur*0.75)
            start = start - rnd
            end = end + (speech_dur - rnd)            
        elif kw_spot == 'end':
            rnd = random.uniform(speech_dur*0.75, speech_dur)
            start = start - rnd
            end = end + (speech_dur - rnd)            
        else:
            rnd = random.uniform(0,speech_dur)
            start = start - rnd
            end = end + (speech_dur - rnd)            
    return int(fs * start), int(fs * end)

#path2jsons_dev = get_jsons(path='/aimlx/Datasets/TEDLIUM_release1/dev/final_json')
#path2jsons_test = get_jsons(path='/aimlx/Datasets/TEDLIUM_release1/test/final_json')
#path2jsons_train = get_jsons(path='/aimlx/Datasets/TEDLIUM_release1/train/final_json')

path2wordcounts = ['/aimlx/Datasets/TEDLIUM_release1/dev/dev_word_count.json', '/aimlx/Datasets/TEDLIUM_release1/test/test_word_count.json',
                   '/aimlx/Datasets/TEDLIUM_release1/train/train_word_count.json']

# Compute word frequencies for train, test and dev set

#word_count(path2jsons_dev, output=path2wordcounts[0])
#word_count(path2jsons_test, output=path2wordcounts[1])
#word_count(path2jsons_train, output=path2wordcounts[2])
#_ = overall_word_count(path2wordcounts, save_result=True)

most_common_words = ['zucchini', 'accountable', 'deliberatly', 'democrats', 'delightful']
#with open('1000-midlong', 'r') as thousend_words:
#    for word in thousend_words:
#        most_common_words.append(word.strip())


path2jsons = get_jsons(path='/aimlx/Datasets/TEDLIUM_release-3/data/final_json/')
Parallel(n_jobs=12)(delayed(extract_kw_train)(keyword, path2jsons) for keyword in most_common_words)
