import socket
import asyncio
import websockets
import json
import time

# Socket绑定、监听端口
server = socket.socket()
server.bind(('', 20019))
server.listen()

# CRC校验算法


def calc_crc(bytedata):
    data = bytearray(bytedata)
    crc = 0xFFFF
    for pos in data:
        crc ^= pos
        for i in range(8):
            if ((crc & 1) != 0):
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return hex(((crc & 0xff) << 8) + (crc >> 8))

# socke服务端接收数据
# 收到的数据格式 21 41 01 00 1A 00 00 00 02 00 80 00 00 03 02 03 E8 00 28 00 6E 0B B8 0B B8 0B B8 00 00 4E 20 00 01 02 03 8B 7D


def recv(conn):
    while True:
        # 如果检测到丢包则重新接收数据
        data = conn.recv(1024)

        # CRC计算 b c为示例0x8B7D拆分转换十进制 即139和125
        checkdata = data[:35]
        crcrecv = calc_crc(checkdata)
        a = crcrecv.encode("utf-8")
        b = int(a[2:4], 16)
        c = int(a[4:6], 16)

        try:
            dataList = list(data)
            # 检测校验码0x8644
            if (dataList[35] == b) & (dataList[36] == c):
                print("数据格式正确，HEX为")
                print(data)
                break
            else:
                print("数据格式错误，校验码错误，请确认")
                continue
        except IndexError:
            print("数据格式错误，长度与预期不符")
    return data

# 通信协议解析计算


def Webdata(dataList):

    now = time.localtime()
    nowt = time.strftime("%Y-%m-%d-%H:%M:%S", now)

    WebdataList = []
    WebdataList.append(nowt)                             # 当前时间
    WebdataList.append(dataList[8])                      # 当前状态
    # 用于前端判定
    '''计算数值
      0 空闲
      1 启动
      2 运行
      3 故障
      4 故障锁死
      5 停机
      '''
    WebdataList.append(dataList[10])                     # 当前故障
    '''计算数值
      0 无故障
      1 过压
      2 欠压
      4 过载
      8 过温
      32 输出缺项
      64 输出短路
      128 风机堵转
      '''
    WebdataList.append(dataList[13])                     # 输入源
    '''计算数值
      0 未识别
      1 DC 110V
      2 DC 600V
      3 AC 380V
      '''
    WebdataList.append(dataList[14])                     # 运行模式
    '''计算数值
      0 停机
      1 设置转速
      2 风量等级
      3 电压调速
      '''
    WebdataList.append(dataList[15]*16*16+dataList[16])  # 转速
    WebdataList.append(dataList[17]*16*16+dataList[18])  # NTC温度
    WebdataList.append(dataList[19]*16*16+dataList[20])  # 母线电压
    WebdataList.append(dataList[21]*16*16+dataList[22])  # U相电流
    WebdataList.append(dataList[23]*16*16+dataList[24])  # V相电流
    WebdataList.append(dataList[25]*16*16+dataList[26])  # W相温度
    WebdataList.append(dataList[29]*16*16+dataList[30])  # 运行时间
    WebdataList.append(dataList[32]*100+dataList[33]
                       * 10+dataList[34])                # 协议版本
    WebdataList.append(dataList[0])                      # 风机编号
    return WebdataList


# 主函数 循环等待socket客户端发来消息

if __name__ == '__main__':
    while True:
        conn, addr = server.accept()
        while True:
            async def echo(websocket, path):
                while True:
                    data = recv(conn)
                    dataList = list(data)
                    print("数据转换DEC存入数组后为")
                    print(dataList)

                    # 转码json发送数据给前端
                    MessageJson = json.dumps(Webdata(dataList))
                    await websocket.send(MessageJson)
                    await asyncio.sleep(3)

                    # 从前端接收json数据
                    MessageReceive = await websocket.recv()
                    MessageReceiveJson = json.loads(MessageReceive)

                    # 打印json解码后的数组
                    print("收到前端数据")
                    print(MessageReceiveJson)

                    # dec数据转换hex  表示未添加CRC校验码的值
                    bytedatabefore = bytes(MessageReceiveJson)

                    # 计算CRC校验值并加入到MessageReceiveJson数组中
                    crcstr = calc_crc(bytedatabefore)
                    t = crcstr.encode("utf-8")
                    x = int(t[2:4], 16)
                    y = int(t[4:6], 16)
                    MessageReceiveJson.append(x)
                    MessageReceiveJson.append(y)

                    # dec数据转换hex  已添加CRC校验码的值
                    bytedata = bytes(MessageReceiveJson)

                    # 发送hex格式给Socket客户端
                    conn.send(bytedata)

            start_server = websockets.serve(echo, '', 20020)
            asyncio.get_event_loop().run_until_complete(start_server)
            asyncio.get_event_loop().run_forever()
