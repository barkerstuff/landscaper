#!/usr/bin/env python3

'''Copyright 2020 Jason Barker
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.'''

import argparse
import os
import sys
from shutil import which
import subprocess
import re
from random import choice
import signal

# Password when zipping files with 7zip
password="supersekretsauce"
image_types = ['png', 'jpg']
output_formats = ['png', 'jpg']

parser = argparse.ArgumentParser(description='This script will take 2 image files or a target folder and find portrait images to join into a landscape. \
                When using auto mode it will traverse directories and automatically join them.')
parser.set_defaults(delete_originals=False, zip_originals=False, output_format="png", password=True)

parser.add_argument('--first', '-1', type=str, help="First image to pass. If using auto mode this selects a target directory to recurse into.")
parser.add_argument('--second', '-2', type=str, help="Second image to pass. Does nothing if using auto mode!")
parser.add_argument('--zip_originals', '-z', action='store_true', help="7Zip the original files making up this montage and delete the original. Password can be changed by editing the top of the script.")
parser.add_argument('--delete_originals', '-d', action='store_true', help="Delete the original files making up this montage.")
parser.add_argument('--auto', '-a', action='store_true', help="Specify a target directory and the script goes to town, joining all portraits it can into landscapey goodness!")
parser.add_argument('--verbose', '-v', action='store_true', help="Enable verbose mode for debugging.")
parser.add_argument('--output_format', '-o', type=str, help="Specify the format.  Accepted value are one of the following of \"{}\". Defaults to png if unspecified.".format("\" or \"".join(output_formats)))
parser.add_argument('--dry', '-s', action='store_true', help="Do not call image magick and quit as soon as 2 valid matching files are found.  For debug purposes.")
parser.add_argument('--nopassword', '-n', action='store_true', help="Do not use a password when calling 7zip.")
parser.add_argument('--resize', '-r', action='store_true', help="Will scale images if the sizes do not match, as long as the 2 images have the right aspect to be merged into landscape. This will incur some minimal destructive losses due to interger pixel scaling.")

args = parser.parse_args()

args.first = os.path.abspath(args.first)
if not args.auto:
    args.second = os.path.abspath(args.second)

# Initial checks
if args.verbose:
    print('Starting initial checks...')
if args.output_format not in output_formats:
    sys.exit('You must specify one of the followimg supported output types: {}'.format(output_formats))
if not os.path.isfile(args.first) and not args.auto:
    sys.exit('First file does not exist. Exiting.')
if not os.path.isdir(args.first) and args.auto:
    sys.exit('Target directory does not exist!. Exiting.')
if not os.path.splitext(args.first)[1].lower() not in image_types:
    sys.exit('First file is not one of the types of valid image files. Exiting')
if not args.auto:
    if os.path.isfile(args.second):
        sys.exit('Second file does not exist. Exiting.')
    if not os.path.splitext(args.second)[1].lower() not in image_types:
        sys.exit('Second file is not one of the types of valid image files. Exiting.')
if args.second and args.auto:
    sys.exit('Do not pass a file argument when using automatic mode! Exiting.')

# Check if imagemagick is present
if not which('magick'):
    sys.exit('It doesn\'t seem that ImageMagick is installed.  Please install this dependency before continuing.')
# Check if imagemagick is present if using args.zip
if not which('7z') and args.zip_originals:
    sys.exit('It doesn\'t seem that 7z is installed.  Please install this dependency before continuing.')

if args.verbose:
    print('Finished initial checks...')

def clear(*params):
    sys.exit('Caught interrupt..!')

def aspect_checker(imagepath):
    ''' Takes an image path and returns whether it is lanscape or portrait '''
    if args.verbose:
        print('In aspect_checker() to check {}'.format(imagepath))
    if os.path.exists(imagepath):
        output = subprocess.check_output(['magick', 'identify', imagepath]).decode()
        resolution = re.findall(r"[0-9]{2,6}x[0-9]{2,6}\+[0-9]\+[0-9]", output)[0]

        x = re.findall(r"[0-9]{2,6}", resolution)[0]
        y = re.findall(r"[0-9]{2,6}", resolution)[1]
        aspect = int(x) / int(y)

        if aspect < 0.9:
            return x, y, "portrait"
        else:
            return x, y, "landscape"
        return False

def transform_images(first, second, first_y, second_y):
    '''Takes two imagepaths pointing to images of same aspect to be recombined into a landscape image'''
    # Transforms 2 portrait images into a landscape
    #if args.verbose:
    #    print('Calling imagemagick on {} and {}!'.format(first, second))
    new_filename = os.path.dirname(first) + os.sep + os.path.splitext(os.path.basename(first).split('os.sep')[0])[0] + '_montage' + os.path.splitext(first)[1]

    if not args.resize:
        if not os.path.exists(new_filename):
            subprocess_list = ['convert', '-format', args.output_format, first, second, '+append', new_filename]
            print('Calling imagemagick on {} and {}!'.format(first, second))
            subprocess.call(subprocess_list)
        else:
            if args.verbose:
                print('Skipping since target montage file exists!')

    elif args.resize:
        # Basically this does the following:
        # 1) Upscale smaller sized image while constraining proportions to the height of the larger
        # 2) Append as normal
        if not os.path.exists(new_filename):
            # Scaling step
            if first_y > second_y:
                smaller_image = first; larger_image = second
                resize_factor = str((int(second_y) / int(first_y)) * 100) + '%'
            else:
                smaller_image = second; larger_image = first
                resize_factor = str((int(first_y) / int(second_y)) * 100) + '%'
            if args.verbose:
                print('Smaller image: {}'.format(smaller_image))
                print('Larger image: {}'.format(larger_image))
                print('Attempting resize of smaller image to match vertical height of first...')
            subprocess_list = ['convert', '-format', args.output_format, smaller_image, '-scale', str(resize_factor), smaller_image]
            subprocess.call(subprocess_list)
            # Append Step as usual
            subprocess_list = ['convert', '-format', args.output_format, first, second, '+append', new_filename]
            print('Calling imagemagick on {} and {}!'.format(first, second))
            subprocess.call(subprocess_list)
        else:
            if args.verbose:
                print('Skipping since target montage file exists!')

    if args.verbose:
        print('Transform_images() finished.')

def zip_originals(first, second):
    if args.verbose:
        print('Entered zip_originals()')
    print('Zipping originals...')
    def zip(i):
        #zip_path = os.path.splitext(i)[0] + '_premontage.7z'
        zip_path = os.path.dirname(i) + os.sep + 'premontage' + os.sep + os.path.splitext(os.path.basename(i))[0] + '.7z'

        if not args.nopassword:
            subprocess_list = ['7z', 'a', '-bb0', '-sdel', '-p{}'.format(password), zip_path, i]
        elif args.password:
            subprocess_list = ['7z', 'a', '-bb0', '-sdel', zip_path, i]
        if args.verbose:
            print(" ".join(subprocess_list))
        try:
            subprocess.call(subprocess_list)
        except Exception as E:
            print(E, 'ERROR: Zip failure!')

    zip(first); zip(second)

    if args.verbose:
        print('Finished zip_originals()')

def delete_originals(first, second):
    if os.path.isfile(first):
        try:
            os.remove(first)
        except Exception as E:
            print(E, 'Failed to delete first original file.')
            sys.exit()
    if os.path.isfile(second):
        try:
            os.remove(second)
        except Exception as E:
            print(E, 'Failed to delete second original file.')
            sys.exit()

def main():

    def join_checker(first, second):
        ''' This is the main driver function that will take 2 images and return a landscaped montage.'''
        if args.verbose:
            print('Entered join_images() function...')

        # Check image aspects and return the x horizontal pixel length
        try:
            first_x, first_y, first_aspect = aspect_checker(first)
            second_x, second_y, second_aspect = aspect_checker(second)
        except:
            # In the event of a bad return just set it so that nothing happens
            # I.e. flag one as portrait and one as landscape
            first_aspect = True; second_aspect = False
            first_x = True; second_x = False
            first_y = False; second_y = True

        # If image aspects do not match then quit
        if first_aspect == "landscape" and second_aspect == "landscape":
            matched = 0
            if args.verbose:
                print("Aspect is landscape! This tool wants portrait images only!")
        elif first_aspect == second_aspect and first_aspect == "portrait" and second_aspect == "portrait":
            if args.verbose:
                print('Aspects match and both are portrait.  Great!')
            matched = 1

        if args.resize:
            if first_aspect == "portrait" and second_aspect == "portrait":
                matched = 1
            else:
                matched = 0

        # If images different size then quit, as long as not passing the args.resize function
        if not args.resize:
            if matched and first_x != second_x:
                if args.verbose:
                    print('The first image is a different horizontal length than the second! Flipping matched to 0')
                matched = 0
            elif matched and first_x == second_x:
                if args.verbose:
                    print('Horizontal sizes match.  Great! Flipping matched to 1')
                matched = 1

        if args.verbose:
            print('Leaving join_checker() function.')
        return matched, first_y, second_y

    def join_images(first, second, first_y, second_y):
        # Convert images
        if matched:
            if args.dry:
                print('Dry mode, doing nothing!')
            transform_images(first, second, first_y, second_y)

        # Zip or delete originals
        if matched and args.delete_originals:
            delete_originals(first, second)
        elif matched and args.zip_originals:
            zip_originals(first, second)

        if args.verbose:
            print('Left join_images() function...')

    # MAIN LOOP BEGINS HERE
    if args.verbose:
        print('Started main() function...')

    if args.auto:
        signal.signal(signal.SIGINT, clear)

        if args.verbose:
            print('main(): in the args.auto section')

        # Create a listing of all subdirectories
        dirlist = [args.first]
        for root, dirs, files in os.walk(args.first):
            for dir in dirs:
                dirlist.append(root + os.sep + dir)
        if args.verbose:
            print('main(): Finished creating dirlist.')

        # Build a list of all images at the same directory depth
        def imagelist_build(imagedir):
            imagelist = []
            if args.verbose:
                print('main(): Selected {} as image folder'.format(imagedir))

            for file in os.listdir(imagedir):
                full_path = imagedir + os.sep + file
                if os.path.isfile(os.path.abspath(full_path)) and os.path.splitext(file)[1].replace('.','') in image_types and 'montage' not in file:
                    imagelist.append(full_path)
                    if args.verbose:
                        print('Adding image file {} in directory {}'.format(file, imagedir))

            if args.verbose:
                print('main(): Finished creating list of images in selected directory.')
            return imagelist

        # Identify 2 suitable images from the imagelist
        if args.verbose:
            print('main(): Trying to find sutable images...')

        # Create imagelist for each directory at a time
        for imagedir in dirlist:
            imagelist = imagelist_build(imagedir)
            if len(imagelist) > 1:
                for a in imagelist:
                    for b in imagelist:
                        a_depth = a.count(os.path.sep)
                        b_depth = b.count(os.path.sep)

                        if a == b:
                            matched = 0
                        else:
                            matched, first_y, second_y = join_checker(a, b)

                        if matched:
                            join_images(a, b, first_y, second_y)
                            try:
                                imagelist.remove(a); imagelist.remove(b)
                            except Exception as E:
                                print(E)

    elif not args.auto:
        join_images(args.first, args.second)

if __name__ == "__main__":
    main()

