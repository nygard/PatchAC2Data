#!/usr/bin/python

# patch-ac2-data v1
#
# Copyright (c) 2012 Steve Nygard
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
#     The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
#     THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#     FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#     LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#     THE SOFTWARE.

import struct
import binascii
import time
import math
import Image # PIL 1.1.7 <http://www.pythonware.com/products/pil/>

class AC2Exception(Exception):
    pass

class AC2FileEntry:
    def __init__(self, identifier, offset, size, mtime):
        self.identifier = identifier
        self.offset     = offset
        self.size       = size
        self.mtime      = mtime

    def __str__(self):
        return "AC2FileEntry <identifier: %08x, offset: %08x, size: %08x, mtime: %08x -- %s>" % (self.identifier, self.offset, self.size, self.mtime, time.ctime(self.mtime))

class AC2Directory:
    def __init__(self, dataFile, offset):
        self.offset = offset
        self.subdirectoryOffsets = []
        self.files = []

        # 62*4 + 4 + 62*16 = 1244
        buf = dataFile.readDataFromBlocks(offset, 1244)
        count, = struct.unpack_from("<I", buf, 248) # 62*4=248
        self.count = count
        #print "count:", count

        self.subdirectoryOffsets = struct.unpack_from("<62I", buf, 0)

        if 0:
            print "offsets:", ", ".join(["%08x" % offset for offset in self.subdirectoryOffsets])
        for index in range(0, count):
            (identifier, offset, size, mtime) = struct.unpack_from("<4I", buf, 252 + 16 * index)
            #print "%2u: %08x %08x %08x %08x" % (index, identifier, offset, size, mtime)
            fileEntry = AC2FileEntry(identifier, offset, size, mtime)
            #print "%2u: %s" % (index, fileEntry)
            self.files.append(fileEntry)

    def __str__(self):
        return "AC2Directory at %08x, count: %u, file count: %u, leaf? %s" % (self.offset, self.count, len(self.files), self.subdirectoryOffsets[0] == 0)

    def data(self):
        buf = ""
        for sdo in self.subdirectoryOffsets:
            buf += struct.pack("<I", sdo)
        #buf += struct.pack("<62I", self.subdirectoryOffsets)
        buf += struct.pack("<I", len(self.files))
        for fe in self.files:
            buf += struct.pack("<4I", fe.identifier, fe.offset, fe.size, fe.mtime)
        for index in range(len(self.files), 62):
            buf += struct.pack("<4I", 0, 0, 0, 0)
        return buf

class AC2DataFile:
    """A simple class to allow data replacement in Asheron's Call 2 data files."""

    def __init__(self, filename):
        self.fileHandle = open(filename, "rb+")
        #print self.fileHandle
        self.fileHandle.seek(0x12c)
        buf = self.fileHandle.read(4*9)
        #print "read buf:", binascii.hexlify(buf)
        magic, blockSize, fileSize, contentType, contentSubtype, firstFreeBlock, lastFreeBlock, freeBlockCount, rootOffset = struct.unpack("<9I", buf);
        if magic != 0x00005442:
            raise AC2Exception("Bad magic number for an AC2 data file")
        self.blockSize      = blockSize
        self.fileSize       = fileSize
        self.contentType    = contentType
        self.contentSubtype = contentSubtype
        self.firstFreeBlock = firstFreeBlock
        self.lastFreeBlock  = lastFreeBlock
        self.freeBlockCount = freeBlockCount
        self.rootOffset     = rootOffset
        self.cachedVersion  = None
        self.dirty          = False

    def __del__(self):
        #print "Destructing AC2DataFile, flushing..."
        #self.flush()
        pass

    def flush(self):
        if self.dirty and self.fileHandle:
            #print "Dirty, must write header."
            self.writeHeader()

    def close(self):
        self.flush()
        self.fileHandle.close()

    def writeHeader(self):
        buf = struct.pack("<9I", 0x00005442, self.blockSize, self.fileSize, self.contentType, self.contentSubtype, self.firstFreeBlock, self.lastFreeBlock, self.freeBlockCount, self.rootOffset)
        #print "buf len:", len(buf)
        self.fileHandle.seek(0x12c)
        self.fileHandle.write(buf)
        self.dirty = False

    def version(self):
        if self.cachedVersion == None:
            dir, versionFE = df.searchForFileEntry(0xffff0001)
            data = self.readDataFromBlocks(versionFE.offset, versionFE.size)
            self.cachedVersion = struct.unpack("<2I", data)[0]
        return self.cachedVersion

    def __str__(self):
        return "file: %s, blockSize: %u, fileSize: %u, contentType: %08x, contentSubtype: %08x, firstFreeBlock: %08x, lastFreeBlock: %08x, freeBlockCount: %u, rootOffset: %08x, dataVersion: %u, freeSpace: %u" % (self.fileHandle.name, self.blockSize, self.fileSize, self.contentType, self.contentSubtype, self.firstFreeBlock, self.lastFreeBlock, self.freeBlockCount, self.rootOffset, self.version(), self.freeSpace())

    def readDataFromBlocks(self, offset, expectedLength):
        blockData = ""
        self.fileHandle.seek(offset)
        nextBlock = offset
        while nextBlock != 0:
            #print "nextBlock: %08x" % nextBlock
            if (nextBlock % self.blockSize) != 0:
                raise AC2Exception("Block offset %08x does not begin on a block boundary" % (nextBlock))
            if nextBlock < self.blockSize or nextBlock >= self.fileSize:
                raise AC2Exception("Block offset %08x does not fall within data area of file (%08x - %08x)" % (nextBlock, blockSize, fileSize))
            if (nextBlock & 0x80000000) != 0:
                raise AC2Exception("Block chain starting at %08x contains free block %08x" % (offset, nextBlock))
            nextBlock = struct.unpack("<I", self.fileHandle.read(4))[0]
            blockData += self.fileHandle.read(self.blockSize-4)

        if len(blockData) < expectedLength:
            raise AC2Exception("Data length (%lu) is shorter than expected (%u)" % (len(blockData), expectedLength))
        if len(blockData) > expectedLength:
            blockData = blockData[:expectedLength]
        return blockData

    def root(self):
        return AC2Directory(self, self.rootOffset)

    def searchForFileEntry(self, identifier):
        """Returns a tuple of (directory, fileEntry)."""
        return self._searchForFileEntry(identifier, self.rootOffset)

    def _searchForFileEntry(self, identifier, offset):
        """Returns a tuple of (directory, fileEntry)."""
        #print "Searching for %08x starting at %08x" % (identifier, offset)
        directory = AC2Directory(self, offset)
        while True:
            #print
            #print directory
            subdirIndex = 0
            searchLeftSubdir = False
            for fileEntry in directory.files:
                #print "%2u: Checking: %s" % (subdirIndex, fileEntry)
                if fileEntry.identifier == identifier:
                    #print "Found!", fileEntry
                    return (directory, fileEntry)
                if identifier < fileEntry.identifier:
                    #print "check left, cur dir is", directory
                    subdirectoryOffset = directory.subdirectoryOffsets[subdirIndex]
                    if subdirectoryOffset == 0:
                        #print "%08x not found" % identifier
                        return (None, None)
                    #print "%08x < %08x, need to check subdirectory %u @ %08x" % (identifier, fileEntry.identifier, subdirIndex, subdirectoryOffset)
                    directory = AC2Directory(self, subdirectoryOffset)
                    searchLeftSubdir = True
                    break
                subdirIndex = subdirIndex + 1
            if not searchLeftSubdir:
                # Need to check the last subdir
                #print "Check last subdir"
                if len(directory.files) < len(directory.subdirectoryOffsets):
                    offset = directory.subdirectoryOffsets[len(directory.files)]
                    directory = AC2Directory(self, offset)
                else:
                    # Not found
                    break
        return (None, None)

    def readDataFromFileEntry(self, fileEntry):
        return self.readDataFromBlocks(fileEntry.offset, fileEntry.size)

    def addFreeBlocks(self, count):
        firstNewBlock = self.fileSize
        currentBlockOffset = self.fileSize
        #print "addFreeBlocks(%u), firstNewBlock: %08x, currentBlockOffset: %08x" % (count, firstNewBlock, currentBlockOffset)
        blockData = "\0" * (self.blockSize - 4)

        # Need to update the last free block to point to the next, newly created free block
        if self.lastFreeBlock != 0:
            buf = struct.pack("<I", firstNewBlock | 0x80000000)
            if 0:
                print "[%08x] Update last free block, write %08x %u, %u" % (self.lastFreeBlock, firstNewBlock | 0x80000000, len(buf), len(blockData))
            self.fileHandle.seek(self.lastFreeBlock)
            self.fileHandle.write(buf)
            self.fileHandle.write(blockData)

        # Now write the free blocks.
        for index in range(0, count):
            nextBlockOffset = 0
            if index < count - 1:
                nextBlockOffset = currentBlockOffset + self.blockSize
            if 0:
                print "Writing free block %4lu (@ %08x) to point to %08x" % (index, currentBlockOffset, nextBlockOffset)
            buf = struct.pack("<I", nextBlockOffset | 0x80000000)
            if 0:
                print "[%08x] Write free block %4lu to point to %08x %u, %u" % (currentBlockOffset, index, nextBlockOffset | 0x80000000, len(buf), len(blockData))
            self.fileHandle.seek(currentBlockOffset)
            self.fileHandle.write(buf)
            self.fileHandle.write(blockData)

            lastBlockOffset = currentBlockOffset
            currentBlockOffset = nextBlockOffset

        if self.firstFreeBlock == 0:
            self.firstFreeBlock = firstNewBlock

        self.freeBlockCount = self.freeBlockCount + count
        self.fileSize = self.fileSize + count * self.blockSize
        self.lastFreeBlock = lastBlockOffset
        self.dirty = True

    def freeSpace(self):
        return self.freeBlockCount * (self.blockSize - 4)

    def ensureAvailableFreeSpace(self, length):
        #print "ensureAvailableFreeSpace(%u), freeSpace: %u" % (length, self.freeSpace())
        if length > self.freeSpace():
            # Add more space to accomodate the data.  Add in 1 MB chunks.
            neededSpace = length - self.freeSpace()

            bytesPerExtension = ((1024 * 1024) / self.blockSize) * (self.blockSize - 4)
            extensions = math.ceil(float(neededSpace) / bytesPerExtension)
            count = int(1024 * 1024 / self.blockSize * extensions)
            if 0:
                print "Need %u bytes more." % neededSpace
                print "bytesPerExtension: %u" % bytesPerExtension
                print "extensions: %u" % extensions
                print "count: %u" % count
            self.addFreeBlocks(count)
            if length > self.freeSpace():
                print "Error: Failed to add enough data to data file. (%u required, %u available)" % (length, self.freeSpace())
            print "after extension:", self
            #self.flush()
        None

    def writeData(self, data, offset):
        """Either over write data with same length, or write to new blocks. If the latter, this assumes there's enough free space available already."""
        #print "writeData(), %u bytes at %08x" % (len(data), offset)
        nextOffset = 0
        blockCount = 0

        isWritingToFreeBlocks = (offset == self.firstFreeBlock)
        remaining = len(data)

        #print "nextOffset: %08x, blockCount: %u, isWritingToFreeBlocks: %s, remaining: %u" % (nextOffset, blockCount, isWritingToFreeBlocks, remaining)

        while remaining > 0:
            #print "remaining:", remaining
            self.fileHandle.seek(offset)
            nextOffset = struct.unpack("<I", self.fileHandle.read(4))[0]
            #print "[%08x] Read next offset: %08x %08x" % (offset, nextOffset, nextOffset & 0x7fffffff)
            if isWritingToFreeBlocks and remaining > self.blockSize - 4 and (nextOffset & 0x80000000) == 0:
                raise AC2Exception("Error: (1) next offset (@ %08x) is NOT marked free: %08x" % (offset, nextOffset))

            self.fileHandle.seek(offset)

            amount = 0;
            nextOffset = nextOffset & 0x7fffffff
            if remaining < self.blockSize - 4:
                self.fileHandle.write(struct.pack("<I", 0))
                amount = remaining
                #print "[%08x] Write last block pointer, remaining data: %u" % (offset, amount)
            else:
                amount = self.blockSize - 4
                self.fileHandle.write(struct.pack("<I", nextOffset))
                #print "[%08x] Write block pointer %08x, remainng data: %u" % (offset, nextOffset, amount)

            #print "[%08x] Write block data, %u bytes" % (offset + 4, amount)
            self.fileHandle.write(data[:amount])
            data = data[amount:]
            remaining = remaining - amount
            blockCount = blockCount + 1
            offset = nextOffset

        if isWritingToFreeBlocks:
            self.freeBlockCount = self.freeBlockCount - blockCount
            self.firstFreeBlock = nextOffset
            if self.firstFreeBlock == 0: # Fails when len(data) is 0
                self.lastFreeBlock = 0

        self.dirty = True

    def freeBlocks(self, offset):
        """Adds the block chain starting at offset to the free blocks."""
        emptyBlockData = "\0" * (self.blockSize - 4)
        currentBlock = offset
        count = 0
        #print "freeBlocks(%08x)" % offset
        while currentBlock != 0:
            self.fileHandle.seek(currentBlock)
            nextBlock = struct.unpack("<I", self.fileHandle.read(4))[0]
            #print "[%08x] nextBlock: %08x" % (currentBlock, nextBlock)

            self.fileHandle.seek(currentBlock)
            if nextBlock == 0:
                #print "[%08x] (a) Writing %08x" % (currentBlock, self.firstFreeBlock | 0x80000000)
                self.fileHandle.write(struct.pack("<I", self.firstFreeBlock | 0x80000000))
            else:
                #print "[%08x] (b) Writing %08x" % (currentBlock, nextBlock | 0x80000000)
                self.fileHandle.write(struct.pack("<I", nextBlock | 0x80000000))

            #print "[%08x] Writing %u empty bytes" % (currentBlock + 4, len(emptyBlockData))
            self.fileHandle.write(emptyBlockData)
            currentBlock = nextBlock
            count = count + 1

        #print "Setting firstFreeBlock to %08x" % offset
        self.firstFreeBlock = offset
        self.dirty = True
        #print "now:", self

    def replaceData(self, directory, fileEntry, newData):
        """Replaces the data for fileEntry with newData.  The directory must be the directory that contains that file entry."""
        #print "-------------------- Ensure available free space"
        self.ensureAvailableFreeSpace(len(newData))
        oldOffset = fileEntry.offset
        fileEntry.offset = self.firstFreeBlock
        fileEntry.size = len(newData)
        #print "-------------------- write new data"
        self.writeData(newData, fileEntry.offset)
        #print "-------------------- rewrite directory", directory
        self.writeDirectory(directory)
        #print "-------------------- free up the old data at %08x" % oldOffset
        # And then free up the old data
        self.freeBlocks(oldOffset)
        #print "-------------------- Done."

    def replaceDataForIdentifier(self, identifier, newData):
        dir, fe = self.searchForFileEntry(identifier)
        self.replaceData(dir, fe, newData)

    def replaceImageForIdentifier(self, identifier, filename):
        """Replaces file <identifier>, which better be an image (type 41), with the image in <filename>.

        Supported image types are JPEG, or other RGB or RGBA images (such as png)."""
        im = Image.open(filename)
        #print im

        if im.format == "JPEG":
            f1 = open(im.filename, "r")
            idata = f1.read()
            f1.close()
            buf = ""
            buf += struct.pack("<6I", identifier, 0, 0, 0, 0x1f4, len(idata))
            buf += idata
            self.replaceDataForIdentifier(identifier, buf)

        elif im.mode == "RGB":
            # Swap the channels.  Can't find an easier way
            pixdata = im.load()
            for y in xrange(im.size[1]):
                for x in xrange(im.size[0]):
                    b, g, r = pixdata[x, y]
                    pixdata[x, y] = (r, g, b)

            buf = ""
            idata = im.tostring()
            buf += struct.pack("<6I", identifier, 0, im.size[0], im.size[1], 0x14, len(idata))
            buf += idata
            df.replaceDataForIdentifier(identifier, buf)

        elif im.mode == "RGBA":
            # Swap the channels.  Can't find an easier way
            pixdata = im.load()
            for y in xrange(im.size[1]):
                for x in xrange(im.size[0]):
                    b, g, r, a = pixdata[x, y]
                    pixdata[x, y] = (r, g, b, a)

            buf = ""
            idata = im.tostring()
            buf += struct.pack("<6I", identifier, 0, im.size[0], im.size[1], 0x15, len(idata))
            buf += idata
            df.replaceDataForIdentifier(identifier, buf)

    def writeDirectory(self, directory):
        buf = directory.data()
        self.writeData(buf, directory.offset)

if 0:
    df = AC2DataFile("test/portal.dat")
    print df

    print df.root()
    print "======================================================================"

    #dir, fe = df.searchForFileEntry(0x41000000)
    #dir, fe = df.searchForFileEntry(0x01000001)
    #dir, fe = df.searchForFileEntry(0x0100001c)

    for identifier in [0x41000000, 0x41000002, 0x41000003, 0x41000004, 0x41000005, 0x41000006, 0x41000007]:
        dir, fe = df.searchForFileEntry(identifier)
        print dir
        print fe
        if fe:
            data = df.readDataFromFileEntry(fe)
            print len(data)
            filename = "out/%08x.dat" % identifier
            f1 = open(filename, "wb")
            f1.write(data)
            f1.close()

if 1:
    df = AC2DataFile("test/portal.dat")
    print df

    #df.replaceDataForIdentifier(0x41000006, buf)
    df.replaceImageForIdentifier(0x41000000, "test-image.png")
    #df.replaceImageForIdentifier(0x41000000, "test-image2.jpeg")
    print "final:", df
    df.close()
