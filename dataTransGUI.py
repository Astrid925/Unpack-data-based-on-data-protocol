"""
Author: cxy
Date: 2022/01/22
实现GUI界面功能：文件输入、参数设置、运行指令（开始/停止）
"""
import tkinter as tk
from tkinter import filedialog,messagebox,ttk
import dataTransformation

dataTransform = tk.Tk()
dataTransform.geometry('500x300')
dataTransform.title('高光谱数据解包软件')

## 文件路径获取
fileOption=tk.LabelFrame(dataTransform, text='文件路径', padx=10, pady=10)
fileOption.place(x=20,y=20)
v1=tk.StringVar()
def fileInput():
    file_input = filedialog.askopenfilename()
    if file_input is not None:
        v1.set(file_input)
    return file_input

inputWindow=tk.Entry(fileOption, width=50,textvariable=v1).grid(column=0,row=0)
tk.Button(fileOption,text='输入文件', command=fileInput).grid(column=1,row=0,padx=5,stick=tk.E)

##################
paramOption=tk.LabelFrame(dataTransform, text='参数设置', padx=10, pady=10)
paramOption.place(x=20,y=100)
ttk.Label(paramOption,text='包长度：').grid(column=0,row=0)
parameter=tk.StringVar()
parameter_list=ttk.Combobox(paramOption,width=8,textvariable=parameter, state='readonly')
parameter_list['values']=(898,1024)
parameter_list.current(0)
parameter_list.grid(column=1,row=0)

##################
processOption=tk.LabelFrame(dataTransform, text='运行指令', padx=10, pady=10)
processOption.place(x=250,y=100)
dataModel = dataTransformation.DataConcat(fileInput(), int(parameter_list.get(),10))
def start ():
    dataModel.openFile()
    dataModel.dataProcess()
    messagebox.showinfo('提示','数据处理完成')
    dataModel.closeFile()

def stop():
    dataModel.closeFile()
    messagebox.showinfo('提示', '停止数据处理')

tk.Button(processOption,text='开始', width=6,command=start).grid(column=0,row=0,padx=5,sticky=tk.W)
tk.Button(processOption,text='停止', width=6,command=stop).grid(column=1,row=0,padx=5,sticky=tk.E)

tk.mainloop()
