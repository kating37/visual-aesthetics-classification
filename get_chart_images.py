import sys
import re
import os
import requests
import billboard
import pylast
import json
import urllib.request
import numpy as np
from datetime import datetime
from urllib.error import HTTPError
from lxml import html
from mochart import gaon, utils


with open('config.json', 'r') as f:
    config = json.load(f)

LASTFM_API_KEY = config['LASTFM']['API_KEY']
LASTFM_API_SECRET = config['LASTFM']['API_SECRET']

network = pylast.LastFMNetwork(api_key=LASTFM_API_KEY,
                               api_secret=LASTFM_API_SECRET)


def getChart(site, genre, date):
    artists = []

    print(f'{genre} - {date}')

    if site == 'billboard':
        chart = billboard.ChartData(genre, date=date)
        for song in chart:
            artists.append(song.artist)
    elif site == 'gaon':
        ranking = gaon.week(day_time=datetime.strptime(date, '%Y-%m-%d'))
        for rank in ranking:
            artists.append(rank['artist'])
    else:
        print('Site must be billboard, gaon, or oricon')
        exit()

    artists = [re.sub('Featuring.*| [xX] .*| & .*', '', artist)
               for artist in artists]
    map(str.strip, artists)

    artists = np.unique(artists)

    return artists


def getImageUrls(artists):
    urls = np.zeros(len(artists), dtype=object)

    for i, artist_name in enumerate(artists):
        try:
            search = network.search_for_artist(artist_name)
            results = search.get_next_page()
            if results:
                artist = results[0]
                url_image = artist.get_url() + '/+images'
                urls[i] = url_image
            else:
                print(artist_name, ' - No URLs')
        except Exception as e:
            print(artist_name, 'Error code:', e.code)
            continue

    return urls


def getImages(site, genre, artists):
    urls = getImageUrls(artists)

    url_base = 'https://lastfm-img2.akamaized.net/i/u/avatar300s/'

    image_dir = './images/' + genre + '/'
    if not os.path.exists(image_dir):
        os.mkdir(image_dir)

    artist_count = len(artists)

    log_file = 'import_' + genre + '.txt'
    file = open(log_file, 'w')

    for i, (artist_name, url_image_list) in enumerate(zip(artists, urls)):
        if url_image_list:
            print(f'({str(i+1).zfill(2)}/{str(artist_count).zfill(2)}) '
                  f'{artist_name} - {url_image_list}')

            artist_name_dir = artist_name.replace(' ', '_').lower()
            artist_name_dir = artist_name_dir.replace('/', '_')

            if 'soundtrack' in artist_name_dir:
                continue

            r = requests.get(url_image_list)
            page_source = r.content
            tree = html.fromstring(page_source)
            results = tree.xpath("//img[@class='image-list-image']/@src")

            artist_image_dir = image_dir + artist_name_dir
            if not os.path.exists(artist_image_dir):
                os.mkdir(artist_image_dir)
                print('NEW')

            for i, path in enumerate(results):
                url_image = url_base + path[49:]  # + '.jpeg#' + path[49:]
                image_filename = '%s/%s-%02d.jpeg' % (artist_image_dir,
                                                      artist_name_dir,
                                                      i+1)

                file.write(image_filename + ' ' + url_image + '\n')

                if not os.path.isfile(image_filename):
                    try:
                        urllib.request.urlretrieve(url_image, image_filename)
                    except HTTPError as e:
                        print(image_filename, 'Error code:', e.code)
                        continue

    file.close()


def main():
    arg_count = len(sys.argv)

    if arg_count == 4:
        site = sys.argv[1]
        genre = sys.argv[2]
        date = sys.argv[3]
        artists = getChart(site, genre, date)  # ie. 'pop-songs'
    elif arg_count == 5:
        site = sys.argv[1]
        genre = sys.argv[2]
        date = sys.argv[3]
        artists = [sys.argv[4]]
    else:
        print('Usage: get_chart_images site chart date [artist]')
        exit()

    getImages(site, genre, artists)


main()
