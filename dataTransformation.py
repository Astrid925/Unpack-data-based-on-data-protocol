"""
Author: cxy
Date: 2022/01/24
解数据包，按照数据协议，将图像数据解包以及拼接图像数据，显示图像数据
"""
import crcmod
import numpy as np
import os
import cv2 as cv
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

class DataConcat():

    def __init__(self, inputPath, pkLen):
        self.inputPath = inputPath
        self.pkLen = pkLen

    def openFile(self):
        self.openFile = open(self.inputPath, mode='rb')
        (file, ext) = os.path.splitext(self.inputPath)
        (Path, filename) = os.path.split(file)
        os.mkdir(Path + '\\' + "Result_" + filename)     #创建一个文件夹
        outPath=Path + '\\' + "Result_" + filename
        self.logPath = os.path.join(outPath, 'log.txt')
        self.logFile = open(self.logPath, mode='w', encoding='utf-8')

        BwritePath = os.path.join(outPath, 'Blue_Band.raw')
        BheadWritePath = os.path.join(outPath, 'Blue_Band.hdr')
        self.BlueFile = open(BwritePath, mode='wb')
        self.BlueHeadFile = open(BheadWritePath, mode='w', encoding='utf-8')
        GwritePath = os.path.join(outPath, 'Green_Band.raw')
        GheadWritePath = os.path.join(outPath, 'Green_Band.hdr')
        self.GreenFile = open(GwritePath, mode='wb')
        self.GreenHeadFile = open(GheadWritePath, mode='w', encoding='utf-8')
        RwritePath = os.path.join(outPath, 'Red_Band.raw')
        RheadWritePath = os.path.join(outPath, 'Red_Band.hdr')
        self.RedFile = open(RwritePath, mode='wb')
        self.RedHeadFile = open(RheadWritePath, mode='w', encoding='utf-8')

    def closeFile(self):
        text = "ENVI\n" + "samples = 1030\n" + "lines=1024\n" + "bands ="+str(self.outCount)+"\n" + "header offset = 0\n" + "file type = ENVI Standard\n" + "data type = 12\n" + "interleave = bsq\n" + "byte order = 1"
        self.BlueHeadFile.write(text)
        self.GreenHeadFile.write(text)
        self.RedHeadFile.write(text)
        self.openFile.close()
        self.logFile.close()
        self.BlueFile.close()
        self.GreenFile.close()
        self.RedFile.close()
        self.BlueHeadFile.close()
        self.GreenHeadFile.close()
        self.RedHeadFile.close()

    def ConcatBGR(self, dataBuf, residualByte, residualColorValue, imageArray, rowNum, colNum):
        dataBuf = residualByte + dataBuf
        temp = len(dataBuf) % 3
        valueBuf = []
        residualByteBuf = bytes()
        if temp == 0:
            for i in range(0, len(dataBuf), 3):
                oneValue = (dataBuf[i] << 4) | ((dataBuf[i + 1] & 0xf0) >> 4)
                twoValue = ((dataBuf[i + 1] & 0x0f) << 8) | dataBuf[i + 2]
                valueBuf += [oneValue, twoValue]
        else:
            for i in range(0, len(dataBuf) - temp, 3):
                oneValue = (dataBuf[i] << 4) | ((dataBuf[i + 1] & 0xf0) >> 4)
                twoValue = ((dataBuf[i + 1] & 0x0f) << 8) | dataBuf[i + 2]
                valueBuf += [oneValue, twoValue]
            residualByteBuf = dataBuf[len(dataBuf) - temp: len(dataBuf)]

        colorValue = residualColorValue + valueBuf
        residualColorBuf = []
        temp = len(colorValue) % 3
        if temp == 0:
            for i in range(0, len(colorValue), 3):
                imageArray[rowNum][colNum] = [colorValue[i], colorValue[i + 1], colorValue[i + 2]]
                colNum += 1
        else:
            for i in range(0, len(colorValue) - temp, 3):
                imageArray[rowNum][colNum] = [colorValue[i], colorValue[i + 1], colorValue[i + 2]]
                colNum += 1
            residualColorBuf = colorValue[len(colorValue) - temp:len(colorValue)]
        return residualByteBuf, residualColorBuf, imageArray, colNum

    def imageLinearStretch(self,image):
        (b, g, r) = cv.split(image)
        def grayProcess(gray, truncated_value=2, maxout=255, minout=0):  # Linear2% 线性拉伸
            low_value = np.percentile(gray, truncated_value)
            high_value = np.percentile(gray, 100 - truncated_value)
            truncated_gray = np.clip(gray, low_value, high_value)
            processed_gray = ((truncated_gray - low_value) / (high_value - low_value)) * (maxout - minout)
            return processed_gray

        bResult = grayProcess(b)
        gResult = grayProcess(g)
        rResult = grayProcess(r)
        imageResult = cv.merge((bResult, gResult, rResult))
        return np.uint8(imageResult),np.uint8(bResult),np.uint8(gResult),np.uint8(rResult)

    def dataProcess(self):
        fileSize = os.path.getsize(self.inputPath)
        dataLen = 876
        crcLen = 2
        headLen = 4
        row = 1024
        col = 1024
        channel = 3
        rowAuxNum = 6
        lineLen = 4620
        lineheadLen = 10
        pkHeadLen = 20  # 在数据之前传输的字节个数
        frameHeadLen = 48  # 帧开始的辅助数据
        zeroDataNum = 344  # 帧结束时0数据个数
        startIdx = 0
        pkFrameTemp = -1
        self.outCount =0
        if self.pkLen==1024:
            auxDataLen=126
        else:
            auxDataLen=0

        font = FontProperties(fname=r"C:\Windows\Fonts\simhei.ttf", size=12)
        plt.ion()
        plt.figure(figsize=(8, 8.5))
        imageBuf = (bytes(), [], np.zeros((row, col, channel), dtype=np.uint16, order='C'), 0)   # 初始化 imageBuf
        auxBuf = np.zeros((row, rowAuxNum), dtype=np.uint16, order='C')
        endByte = b'\xFB\xFB'
        startByte = b'\xFD\xFD\x04\x00\x00\x55'
        crc16 = crcmod.mkCrcFun(0x11021, initCrc=0xFFFF, rev=False, xorOut=0x0000)
        while True:
            finishFlag = 0
            while True:
                if startIdx >= fileSize - headLen:
                    print("已到文件末尾!")
                    self.openFile.close()
                    self.logFile.close()
                    finishFlag = 1
                    break
                else:
                    self.openFile.seek(startIdx, 0)
                    headContent = self.openFile.read(headLen)
                    if headContent.hex() == '1acffc1d':
                        startIdx = startIdx + self.pkLen
                        break
                    else:
                        startIdx = self.openFile.tell() - (headLen - 1)
            if finishFlag == 1:
                break
            self.openFile.seek(self.openFile.tell() - headLen, 0)
            pkBuf = self.openFile.read(self.pkLen)
            dataBuf = pkBuf[pkHeadLen:self.pkLen - crcLen-auxDataLen]  # 图像数据
            dataStr = dataBuf.hex()
            newPkStart = dataStr.find('1acffc1d')  # 判断当前databuf是否存在其他帧头v
            if newPkStart == -1:
                dataBuf = dataBuf
                crcBuf = pkBuf[headLen:self.pkLen - crcLen-auxDataLen]  # crc 校验数据
                crcValue = pkBuf[self.pkLen - auxDataLen-crcLen:self.pkLen-auxDataLen]
                pkFrameNum = int(pkBuf[headLen + 2:headLen + 5].hex(), 16)
            else:
                startIdx = startIdx - self.pkLen + headLen  # 从包头以后的地址开始
                continue
            frameHeaderStart = dataStr.find('fdfd7f7f7f7f')
            if frameHeaderStart != -1:
                pass
            else:
                if (pkFrameNum - pkFrameTemp) > 1:  # 判断是否有包丢失
                    if 'frameNum' in vars().keys():
                        lossPkNum = pkFrameNum - pkFrameTemp - 1
                        self.logFile.write(str(frameNum + 1) + "帧" + str(rowNum + 1) + "行" + "丢失" + str(lossPkNum) + "包数据！！\n")
                        for i in range(lossPkNum):
                            appendData = bytes(0 for j in range(dataLen))  # 丢失的包用0填充
                            pkNum = (pkFrameTemp + i + 1) % int('001519', 16)
                            bytesNum = ((pkNum + 1) * dataLen - frameHeadLen) % lineLen
                            if bytesNum < dataLen:
                                if bytesNum == 0:
                                    lineEndDataBuf = appendData[0:dataLen - 2]
                                    imageBuf = self.ConcatBGR(lineEndDataBuf, imageBuf[0], imageBuf[1], imageBuf[2], rowNum,imageBuf[3])
                                    auxBuf[rowNum, rowAuxNum - 1:rowAuxNum] = [int(x) << 8 | int(y) for x, y in zip(endByte[0::2], endByte[1::2])]
                                else:
                                    endPos = dataLen - bytesNum
                                    endDataBuf = appendData[0:endPos - 2]
                                    imageBuf = self.ConcatBGR(endDataBuf, imageBuf[0], imageBuf[1], imageBuf[2], rowNum,imageBuf[3])
                                    auxBuf[rowNum, rowAuxNum - 1:rowAuxNum] = [int(x) << 8 | int(y) for x, y in zip(endByte[0::2], endByte[1::2])]
                                    if rowNum == 1023:  # 有些帧数据丢失了帧尾标识
                                        imageArray = imageBuf[2]
                                        BimageArray = np.concatenate((auxBuf[:, 0:rowAuxNum - 1], imageArray[:, :, 0],auxBuf[:, rowAuxNum - 1:rowAuxNum]), axis=1)
                                        GimageArray = np.concatenate((auxBuf[:, 0:rowAuxNum - 1], imageArray[:, :, 1],auxBuf[:, rowAuxNum - 1:rowAuxNum]), axis=1)
                                        RimageArray = np.concatenate((auxBuf[:, 0:rowAuxNum - 1], imageArray[:, :, 2],auxBuf[:, rowAuxNum - 1:rowAuxNum]), axis=1)

                                        self.BlueFile.write(BimageArray.astype('>u2'))
                                        self.GreenFile.write(GimageArray.astype('>u2'))
                                        self.RedFile.write(RimageArray.astype('>u2'))
                                        self.outCount += 1
                                        imageBuf = ( bytes(), [], np.zeros((row, col, channel), dtype=np.uint16, order='C'),0)  # 数据清零
                                        auxBuf = np.zeros((row, rowAuxNum), dtype=np.uint16, order='C')
                                        del frameNum
                                        break
                                    else:
                                        rowNum = rowNum + 1  # 开始新的一行

                                    auxBuf[rowNum, 0:rowAuxNum - 1] = [int(x) << 8 | int(y) for x, y in zip(startByte[0::2], startByte[1::2])] + [frameNum, rowNum]
                                    colNum = 0
                                    startDataBuf = appendData[endPos + lineheadLen:dataLen]
                                    residualByte = bytes()
                                    residualColorValue = []
                                    imageBuf = self.ConcatBGR(startDataBuf, residualByte, residualColorValue, imageBuf[2],rowNum, colNum)
                            elif bytesNum == dataLen:
                                rowNum = rowNum + 1  # 开始新的一行
                                colNum = 0
                                auxBuf[rowNum, 0:rowAuxNum - 1] = [int(x) << 8 | int(y) for x, y in zip(startByte[0::2], startByte[1::2])] + [frameNum,rowNum]
                                lineStartDataBuf = appendData[lineheadLen:dataLen]
                                residualByte = bytes()
                                residualColorValue = []
                                imageBuf = self.ConcatBGR(lineStartDataBuf, residualByte, residualColorValue, imageBuf[2],rowNum, colNum)
                            else:
                                imageBuf = self.ConcatBGR(appendData, imageBuf[0], imageBuf[1], imageBuf[2], rowNum,imageBuf[3])
                    else:
                        continue
                else:
                    pass

            pkFrameTemp = pkFrameNum
            # 数据转换和拼接
            if dataBuf[0:6].hex() == 'fdfd7f7f7f7f':
                frameNum = int(dataBuf[10:12].hex(), 16)
                frameCount = int(pkFrameNum / int('001519', 16))
                imageBuf = (bytes(), [], np.zeros((row, col, channel), dtype=np.uint16, order='C'), 0)  # 数据清零，对于之前没有完整一帧的数据清零
                if frameNum == frameCount:
                    frameFlag = 0
                    frameStartData = dataBuf[frameHeadLen:dataLen]
                    if frameStartData[0:2].hex() == 'fdfd':
                        rowNum = int(frameStartData[lineheadLen - 2:lineheadLen].hex(), 16)
                        auxBuf[rowNum, 0:rowAuxNum - 1] = [int(x) << 8 | int(y) for x, y in zip(frameStartData[0:lineheadLen:2],frameStartData[1:lineheadLen:2])]
                        frameStartData = frameStartData[lineheadLen:len(frameStartData)]
                        imageBuf = self.ConcatBGR(frameStartData, imageBuf[0], imageBuf[1], imageBuf[2], rowNum, imageBuf[3])
                else:
                    continue
            elif dataBuf[dataLen - zeroDataNum - 6:dataLen - zeroDataNum - 4].hex() == 'fbfb' and dataBuf[dataLen - zeroDataNum - 3:dataLen - zeroDataNum].hex() == '7ffbfb':
                if 'frameNum' in vars().keys():
                    frameFlag = 1
                    auxBuf[rowNum, rowAuxNum - 1:rowAuxNum] = [int(x) << 8 | int(y) for x, y in zip(dataBuf[dataLen - zeroDataNum - 6:dataLen - zeroDataNum - 4:2],dataBuf[dataLen - zeroDataNum - 5:dataLen - zeroDataNum - 4:2])]
                    framendDataBuf = dataBuf[0:dataLen - zeroDataNum - 6]
                    imageBuf = self.ConcatBGR(framendDataBuf, imageBuf[0], imageBuf[1], imageBuf[2], rowNum, imageBuf[3])
                    # 显示
                    imageInf = self.imageLinearStretch(imageBuf[2])
                    plt.suptitle(u"第" + str(frameNum + 1) + u"帧图像", fontsize=16, fontproperties=font)
                    plt.subplot(221)
                    plt.axis("off")
                    plt.title(u"RGB彩色图像", fontproperties=font)
                    plt.imshow(imageInf[0])
                    plt.subplot(222)
                    plt.axis("off")
                    plt.title(u"B通道图像", fontproperties=font)
                    plt.imshow(imageInf[1], cmap="gray")
                    plt.subplot(223)
                    plt.axis("off")
                    plt.title(u"G通道图像", fontproperties=font)
                    plt.imshow(imageInf[2], cmap="gray")
                    plt.subplot(224)
                    plt.axis("off")
                    plt.title(u"R通道图像", fontproperties=font)
                    plt.imshow(imageInf[3], cmap="gray")
                    plt.pause(0.02)
                    plt.clf()
                    # 存储
                    imageArray = imageBuf[2]
                    BimageArray = np.concatenate((auxBuf[:, 0:rowAuxNum - 1], imageArray[:, :, 0], auxBuf[:, rowAuxNum - 1:rowAuxNum]), axis=1)
                    GimageArray = np.concatenate((auxBuf[:, 0:rowAuxNum - 1], imageArray[:, :, 1], auxBuf[:, rowAuxNum - 1:rowAuxNum]), axis=1)
                    RimageArray = np.concatenate((auxBuf[:, 0:rowAuxNum - 1], imageArray[:, :, 2], auxBuf[:, rowAuxNum - 1:rowAuxNum]), axis=1)
                    self.BlueFile.write(BimageArray.astype('>u2'))
                    self.GreenFile.write(GimageArray.astype('>u2'))
                    self.RedFile.write(RimageArray.astype('>u2'))
                    self.outCount += 1
                    imageBuf = (bytes(), [], np.zeros((row, col, channel), dtype=np.uint16, order='C'), 0)  # 数据清零
                    auxBuf = np.zeros((row, rowAuxNum), dtype=np.uint16, order='C')
                else:
                    continue
            else:
                if 'frameNum' in vars().keys():
                    pkNum = pkFrameNum % int('001519', 16)  # 相对每一帧，包的数量
                    bytesNum = ((pkNum + 1) * dataLen - frameHeadLen) % lineLen  # 相对每一行的bytes数量
                    if bytesNum >= dataLen:
                        if dataBuf[0:2].hex() == 'fdfd':
                            rowNum = int(dataBuf[lineheadLen - 2:lineheadLen].hex(), 16)  # 开始新的一行
                            auxBuf[rowNum, 0:rowAuxNum - 1] = [int(x) << 8 | int(y) for x, y in zip(dataBuf[0:lineheadLen:2], dataBuf[1:lineheadLen:2])]
                            colNum = 0
                            lineStartDataBuf = dataBuf[lineheadLen:dataLen]
                            residualByte = bytes()
                            residualColorValue = []
                            imageBuf = self.ConcatBGR(lineStartDataBuf, residualByte, residualColorValue, imageBuf[2],rowNum, colNum)
                        else:
                            imageBuf = self.ConcatBGR(dataBuf, imageBuf[0], imageBuf[1], imageBuf[2], rowNum, imageBuf[3])
                    else:
                        if bytesNum == 0:
                            lineEndDataBuf = dataBuf[0:dataLen - 2]
                            imageBuf = self.ConcatBGR(lineEndDataBuf, imageBuf[0], imageBuf[1], imageBuf[2], rowNum,imageBuf[3])
                            auxBuf[rowNum, rowAuxNum - 1:rowAuxNum ] = [int(x) << 8 | int(y) for x,y in zip(dataBuf[dataLen - 2:dataLen:2],dataBuf[dataLen - 1:dataLen:2])]
                        elif bytesNum >= lineheadLen:
                            endPos = dataLen - bytesNum
                            if dataBuf[endPos - 2:endPos].hex() == 'fbfb' and dataBuf[endPos:endPos + 2].hex() == 'fdfd':
                                endDataBuf = dataBuf[0:endPos - 2]
                                auxBuf[rowNum, rowAuxNum - 1:rowAuxNum ] = [int(x) << 8 | int(y) for x,y in zip(dataBuf[endPos - 2:endPos:2],dataBuf[endPos - 1:endPos:2])]
                                imageBuf = self.ConcatBGR(endDataBuf, imageBuf[0], imageBuf[1], imageBuf[2], rowNum,imageBuf[3])
                                rowNum = int(dataBuf[endPos + lineheadLen - 2:endPos + lineheadLen].hex(), 16)  # 开始新的一行
                                auxBuf[rowNum, 0:rowAuxNum - 1] = [int(x) << 8 | int(y) for x,y in zip(dataBuf[endPos:endPos + lineheadLen:2],dataBuf[endPos+1:endPos + lineheadLen:2])]
                                colNum = 0  # 列号清零
                                startDataBuf = dataBuf[endPos + lineheadLen:dataLen]
                                residualByte = bytes()
                                residualColorValue = []
                                imageBuf = self.ConcatBGR(startDataBuf, residualByte, residualColorValue, imageBuf[2],rowNum, colNum)
                        else:
                            print("bytesNum=", bytesNum)
                else:
                    continue
            # crc校验
            crcResult = crc16(crcBuf)
            if crcResult.to_bytes(length=2, byteorder='big') != crcValue:
                frameStr = str(frameNum + 1)
                rowStr = str(rowNum + 1)
                self.logFile.write(frameStr + "帧" + rowStr + "行" + "数据传输错误\n")

            if frameFlag == 1:
                del frameNum
