patch-ac2-data v1
=================

This is a small python script to allow you do replace data in the Asheron's Call 2 data files.
It is intended to make skinning the UI easier.

Requirements
------------

This uses Python, so you need that installed.  I use Mac OS X, but you can download installers
for windows at <http://python.org/download/>.  You should use the 2.7.3 version.

This also requires the Python Image Library, currently version 1.1.7.  You can download an
installer for Windows at <http://www.pythonware.com/products/pil/>.

*Note* I have not tested this on Windows yet, but it should work in theory :)

Usage
-----

If anything goes wrong, this will probably corrupt your data file, so be sure you keep a copy
of your original data files before using this!

patch-ac2-data.py v1

Usage: patch-ac2-data.py <patch directory>


       First of all, be sure to BACK UP your data files.  If anything goes wrong they'll
       likely be left in an unusable state!

       Run this from the directory that contains the Asheron's Call 2 data files.

       <patch directory> is the path to the directory that contains the replacement images,
       and the patch.txt file.  This text file has commands, one per line, case sensitive:

           'datafile <path>'                -- switch to patching the data file at <path>
           'replace <identifer> <filename>' -- replace the <identifier> (specified as hex without a
                                               leading 0x) with the image in <filename>

I also have an archive of all the extracted images, so that you can find the image you want to
replace.  You can download this archive at <http://stevenygard.com/download/ac2/ac2-images-2012-12-27.zip>

Contact
-------

You may contact the author by:

                  e-mail: nygard at gmail.com
   Asheron's Call forums: Lothnar

License
-------

Copyright (c) 2012 Steve Nygard

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
associated documentation files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all copies or
    substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
    BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
    DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
