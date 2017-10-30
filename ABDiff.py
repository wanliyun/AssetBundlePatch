#!/usr/bin/env python
# -*- coding:utf-8 -*-  
#
# create by liwenkun 2017.10.30
# 比较两个版本的AB包并输出其差异文件
# 工作流程：
# 1.分别提取两个版本的文件头和原始Asset文件
# 2.检查是否支持文件头
# 3.比较两个版本的文件头是否完全一致
# 4.将两个版本的原始Asset文件写到硬盘
# 5.使用外部命令bsdiff获得两个文件的差异
#
# 依赖的第三方库:pylzma, lz4
#
# 已经在windows的Python2.7版本测试通过
#
# 已经在Unity5.5.4p4版本的AB包测试通过

import pylzma as lzma
import lz4
import os
import sys

class Stream:
	def __init__(self, content):
		self.content = content
		self.position = 0
	
	def readInt8(self):
		ret = self.content[self.position]
		self.position += 1
		return ret


	def readInt16(self):
		a = self.content[self.position]
		b = self.content[self.position+1]
		self.position += 2
		return ord(a)<<8 | ord(b)

	def readInt32(self):
		a = self.content[self.position]
		b = self.content[self.position+1]
		c = self.content[self.position+2]
		d = self.content[self.position+3]
		self.position += 4
		return ord(a)<<24 | ord(b)<<16 | ord(c)<<8 |  ord(d)

	def readInt64(self):
		hight = self.readInt32()
		low = self.readInt32()
		return hight<<32 | low

	def readString(self):
		startPos = self.position
		while self.content[self.position] != '\0':
			self.position += 1

		retStr = self.content[startPos : self.position]
		self.position += 1
		return retStr

	def readRaw(self,len):
		retStr = self.content[self.position : self.position + len]
		self.position += len
		return retStr

	def readBlock(self, flag,compressSize,unCompressSize = -1):
		flag &= 0x3f
		bRawBytes = None

		if flag == 1:
			p0 = self.readInt8()
			p1 = self.readInt8()
			p2 = self.readInt8()
			p3 = self.readInt8()
			p4 = self.readInt8()
			content = self.readRaw(compressSize - 5)

			lc = p0 % 9
			remainder = int(p0 / 9)
			lp = remainder % 5
			pb = int(remainder / 5)

			dict_size = (p1) | (p2 << 8) | (p3 << 16) | (p4 << 32)

			filter = {
					"lc" : lc, "lp" : lp,	"pb" : pb,	"dict_size" : dict_size,
				}
			my_filters = [
				{"id": lzma.FILTER_LZMA1, "lc" : lc, "lp" : lp,	"pb" : pb,	"dict_size" : dict_size,},
			]

			bRawBytes = lzma.decompress(content,lzma.FORMAT_RAW,None,my_filters)
		elif flag == 2 or flag == 3:
			content = self.readRaw(compressSize)
			bRawBytes = lz4.block.decompress(content, unCompressSize)
		else:
			bRawBytes = self.readRaw(compressSize)
		return bRawBytes

def readFile(fileName):
	f = open(fileName, "rb")
	content = f.read()
	f.close()
	return content

def writeFile(fileName, content):
	f = open(fileName, "wb")
	f.write(content)
	f.close()

def isSameHeader(h1,h2):
	if len(h1) != len(h2):
		return False

	for k in h1.keys():
		v = h1[k]
		if not h2.has_key(k) or h2[k] != v:
			return False

	return True

def Extract(fileName):
	ss = Stream( readFile(fileName) )
	header = {	}

	header["signure"] = ss.readString()
	header["format"] = ss.readInt32()
	header["engine"]  = ss.readString()
	header["version"]  = ss.readString()

	bundleSize = ss.readInt64()
	compressedSize = ss.readInt32()
	uncompressedSize = ss.readInt32()
	flag = ss.readInt32()

	blockInfos = ss.readBlock(flag,compressedSize,uncompressedSize)
	ssb = Stream(blockInfos)

	header["blockHead"]  = ssb.readRaw(0x10)

	blockcount = ssb.readInt32()
	blockList = []
	for i in range(0,blockcount):
		bUSize = ssb.readInt32()
		bSize = ssb.readInt32()
		bFlag = ssb.readInt16()
		blockContent = ss.readBlock(bFlag, bSize, bUSize)
		blockList.append(blockContent)
	
	entrycount = ssb.readInt32()
	assert(entrycount == 1)
	ssb.readInt64()
	ssb.readInt64()
	header["entry_unknown"]  = ssb.readInt32()
	header["entry_filename"]  = ssb.readString()
	return header, b"".join(blockList)



def Diff(v1Path,v2Path,diffPath):
	header1,content1 = Extract(v1Path)
	header2,content2 = Extract(v2Path)
	if not isSameHeader(header1,header2):
		print("Header Not Same")
		return

	tmpFile1 = v1Path+".raw.tmp"
	tmpFile2 = v2Path+".raw.tmp"

	writeFile(tmpFile1, content1)
	writeFile(tmpFile2, content2)

	os.system("bsdiff " + tmpFile1 + " " + tmpFile2 + " " + diffPath)
	os.unlink(tmpFile1)
	os.unlink(tmpFile2)



if __name__ == '__main__':
	if len(sys.argv) != 4:
		print("Usage " + sys.argv[0] + " oldABPath  newABPath  pathPath")
        else:
            Diff(sys.argv[1], sys.argv[2], sys.argv[3])


