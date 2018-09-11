#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=W0105,C0325
'''
Created on Mon Apr 24 08:53:47 2017

@author: Sean.Titmarsh
'''
import sys
reload(sys)  # Reload does the trick!
sys.setdefaultencoding('UTF8')
#Some moron decided to use https://emojipedia.org/large-blue-circle/ in a video title. This protects from that.


import requests
import json
import praw
import sqlite3
import datetime
import os.path

'''
SETTINGS
'''

'''
CHANNELS format:
['File(Table) Name', 'Youtube Channel ID', 'Subreddits to post to', 'Praw.ini site to use']

To set custom settings (filters or rules), add custom flags to praw.ini and access by using
reddit.config.custom['custom_flag'].
'''

CHANNELS = [['Table', 'channelID', ['subreddit'], 'site']]

'''
AUTHENTICATION CREDENTIALS

For YT Credentials, obtain them from https://console.developers.google.com
'''
YT_KEY = ''


'''
AUTHENTICATION FUNCTIONS
'''

'''
Reddit Authentication
OAuth is now supported natively in PRAW, and this script uses the 'SCRIPT' flow at 
https://praw.readthedocs.io/en/latest/getting_started/authentication.html#oauth.

If you want to obsfucate account credentials, you can use Environment Variables or a praw.ini file
as described in https://praw.readthedocs.io/en/latest/getting_started/configuration/prawini.html.
'''
def reddit_oauth(site_name):
    '''
    Uses a praw.ini file in the working directory. Currently formatted as:

    [site_name]
    client_id=
    client_secret=
    password=
    username=
    user_agent=
    '''
    reddit = praw.Reddit(site_name)
    return reddit


'''
YOUTUBE FUNCTIONS
'''

def get_video_id(channel_id):
    '''
    Takes the current channelId, and returns the five ids in
    a list for the next function to use
    Returns take the form: 
    {u'snippet':{u'liveBroadcastContent': u'none', u'title': u'title'},u'id': {u'videoId': u'id'}},
    '''
    url = 'https://www.googleapis.com/youtube/v3/search'
    payload = {'part':'id, snippet',
               'channelId':channel_id,
               'order':'date',
               'access_type':'offline',
               'type':'video',
               'fields':'items(id(videoId),snippet(title, liveBroadcastContent))',
               'key':YT_KEY}
    videos = requests.get(url, params=payload)
    items = json.loads(videos.text)
    return items


'''
REDDIT FUNCTIONS
Note, to work, pass reddit to each function. Otherwise, the praw instance won't be logged in.
'''
def submit_to_subreddit(subreddit, name, link, reddit):
    '''
    Take each YouTube feed entry and submit to Reddit.
    '''
    print('Submitting to {0}: Title:{1}\r'.format(subreddit, name))
    submission = reddit.subreddit(subreddit).submit(title=name, url=link, resubmit='True', send_replies=False)
    return submission.id


'''
DATABASE FUNCTIONS
'''


def setup_database(name):
    conn = sqlite3.connect('Youtube.db')
    c = conn.cursor()
    c.execute('CREATE TABLE ' + name + ' (title text, videoId text, time timestamp, subID text)')
    conn.commit()
    conn.close()

def check_videoId(name, videoId):
    '''

    '''
    conn = sqlite3.connect('Youtube.db')
    c = conn.cursor()
    c.execute('SELECT * FROM ' + name + ' WHERE videoId = (?)', (videoId,))
    line = c.fetchone()
    if line == [] or line is None:
        match = 'None'
    else:
        match = 'Found'
    conn.close()
    return match

def save_videoId(name, videoId, title, submissionId):
    '''

    '''
    match = check_videoId(name, videoId)
    if match != 'Found':
        conn = sqlite3.connect('Youtube.db')
        c = conn.cursor()
        c.execute('INSERT INTO ' + name + ' VALUES(?, ?, ?, ?)', (title, videoId, datetime.datetime.now(), submissionId))
        conn.commit()
        conn.close()


def run_bot():
    '''Start a run of the bot.'''
    
    for channel in CHANNELS:
        print('Now running ' + channel[0] + '\r')
        reddit = reddit_oauth(channel[3])
        print('Logged in to Reddit\r')

        # Check if database exists, and create it if not
        if not (os.path.exists(channel[0] + '.db')):
            print('New Database Setup\r')
            setup_database(channel[0])
        else:
            print('Database exists\r')
        
        #Get list of videos from youtube
        videos = get_video_id(channel[1])
        submitted = 0
        livecount = 0
        old = 0
        for video in videos['items']:
            name = video['snippet']['title']
            print name
            live = video['snippet']['liveBroadcastContent']
            videoId = video['id']['videoId']
            link = 'https://www.youtube.com/watch?v=' + video['id']['videoId']
            present = check_videoId(channel[0], videoId)
            for sub in channel[2]:
                if live != 'none':
                    livecount += 1
                    save_videoId(channel[0], videoId, name, 'LIVESTREAM')
                    continue
                if present != 'Found':
                    print('Now Submitting ' + name+'\r')
                    submissionId = submit_to_subreddit(sub, name, link, reddit)
                    print('Submitted\r')
                    save_videoId(channel[0], videoId, name, str(submissionId))
                    submitted += 1
                    continue
                else:
                    old += 1
                    continue
        print('Channel Complete: {0} Submitted, {1} Old, {2} Live\r'.format(submitted, old, livecount))

if __name__ == '__main__':

    try:
        run_bot()
    except SystemExit:
        print('Exit called.')
