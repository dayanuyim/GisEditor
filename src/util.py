#!/usr/bin/env python3

import tkinter as tk
from PIL import Image, ImageTk, ImageDraw

class AreaSelector:
    @property
    def size(self):
        return self.__size

    @property
    def pos(self):
        return self.__pos

    def __init__(self, canvas, size=None, pos=None):
        self.__canvas = canvas
        self.__button_side = 20
        self.__cv_items = []

        canvas_w = canvas.winfo_width()
        canvas_h = canvas.winfo_height()

        #size
        self.__size = size if size is not None else (round(canvas_w/2), round(canvas_h/2))
        w = self.__size[0]
        h = self.__size[1]
        #pos
        self.__pos = pos if pos is not None else (round((canvas_w-w)/2), round((canvas_h-h)/2))
        x = self.__pos[0]
        y = self.__pos[1]

        #ceate items
        self.__cv_area = self.genAreaImage()
        self.__cv_items.append(self.__cv_area)

        self.__cv_ok = self.genOKButton()
        self.__cv_items.append(self.__cv_ok)

        self.__cv_cancel = self.genCancelButton()
        self.__cv_items.append(self.__cv_cancel)

        #bind
        for item in self.__cv_items:
            canvas.tag_bind(item, "<Button-1>", self.onSelectAreaClick)
            canvas.tag_bind(item, "<Button1-ButtonRelease>", self.onSelectAreaRelease)
            canvas.tag_bind(item, "<Button1-Motion>", self.onSelectAreaMotion)


    #bind motion events
    def onSelectAreaClick(self, e):
        self.__mousepos = (e.x, e.y)

    def onSelectAreaRelease(self, e):
        self.__mousepos = None

    def onSelectAreaMotion(self, e):
        #move
        dx = e.x - self.__mousepos[0]
        dy = e.y - self.__mousepos[1]
        for item in self.__cv_items:
            self.__canvas.move(item, dx, dy)
        #update
        self.__mousepos = (e.x, e.y)

    def genOKButton(self, order=1):
        #anchor ne
        w = self.__pos[0] + self.__size[0] - self.__button_side*order
        h = self.__pos[1]
        return self.__canvas.create_oval(w, h, w+self.__button_side, h+self.__button_side, fill='green')

    def genCancelButton(self, order=2):
        #anchor ne
        w = self.__pos[0] + self.__size[0] - self.__button_side*order
        h = self.__pos[1]
        return self.__canvas.create_oval(w, h, w+self.__button_side, h+self.__button_side, fill='red')

    def genAreaImage(self):
        img = Image.new('RGBA', self.__size, (255,255,0, 128))  #yellow 
        pimg = ImageTk.PhotoImage(img)
        self.__cv_area_img = pimg   #keep refg
        return self.__canvas.create_image(self.__pos, image=pimg, anchor='nw')
