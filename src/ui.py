#!/usr/bin/env python3

import tkinter as tk
import Pmw as pmw
import platform
from PIL import ImageTk

class Dialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)


        #handler
        self._handlers = {}

        #board
        self.geometry('+0+0')
        self.protocol('WM_DELETE_WINDOW', lambda: self._onClosed(None))
        self.bind('<Escape>', self._onClosed)

        #silent update
        self.withdraw()  #hidden
        self._visible = tk.BooleanVar(value=False)

    def show(self):
        #UI
        self.transient(self.master)  #remove max/min buttons
        self.focus_set()  #prevent key-press sent back to parent
        
        self.update()  #update window size

        self.deiconify() #show
        self._visible.set(True)

        self.grab_set()   #disalbe interact of parent
        self.master.wait_variable(self._visible)

    def _onClosed(self, e):
        self.onClosed()
        
        if self.master is not None:
            self.master.focus_set()
        self.grab_release()

        self.destroy()
        #self.withdraw()
        self._visible.set(False)

    #{{ handler
    def invokeHandler(self, name):
        if name in self._handlers:
            self._handlers[name]()

    def addClosedHandler(self, h): self._handlers['closed'] = h;
    def onClosed(self): self.invokeHandler('closed')

        #}} handler

class EditBoard(Dialog):
    COL_TYPE_STR= 0
    COL_TYPE_BOOL= 1
    COL_TYPE_PIC= 2

    @property
    def cols(self):
        return len(self._col_hdrs)

    @property
    def rows(self):
        return len(self._data)

    @property
    def data(self):
        return self._data

    def __init__(self, master, col_hdrs):
        super().__init__(master)

        self._font = 'Arialuni 12'
        self._bfont = 'Arialuni 12 bold'
        self._col_hdrs = col_hdrs
        self._data = []
        self._widgets = {}  #row data->widgets 
        self._var_widgets = {} #var_name->widget
        self._fg_color = 'black'
        self._bg_color = self.cget('bg')
        self._hl_bg_color = 'lightblue'

    def show(self):
        self.init()
        super().show()

    def init(self):
        self._sf = pmw.ScrolledFrame(self, usehullsize = 1, hull_width = 300, hull_height = 600)
        self._sf.pack(fill = 'both', expand = 1)

        frame = self._sf.interior()
        font = self._font
        bfont = self._bfont

        row, col = 0, 0
        #show column headers
        for col_hdr in self._col_hdrs:
            type, title, editable = col_hdr
            tk.Label(frame, text=title, font=bfont).grid(row=row, column=col)
            col += 1

        for row_data in self._data:
            row += 1
            widgets = self.initRowWidgets(row)
            self.initRowData(widgets, row_data)
            self._widgets[row] = widgets

    def initRowWidgets(self, row):
        frame = self._sf.interior()
        bfont = self._bfont
        font = self._font
        widgets = []
        col = 0

        for col_hdr in self._col_hdrs:
            type, title, editable = col_hdr

            #create widget
            if type == self.COL_TYPE_STR and editable:
                w = tk.Entry(frame, font=font, relief='flat', state='disabled',
                        disabledforeground=self._fg_color, disabledbackground=self._bg_color)
                self.setWidgetEditable(w, self._onCellChanged)
            elif type == self.COL_TYPE_STR and not editable:
                w = tk.Label(frame, font=font, anchor='w')
            elif type == self.COL_TYPE_BOOL:
                w = tk.Label(frame, font=bfont, anchor='e')
            elif type == self.COL_TYPE_PIC:
                w = tk.Label(frame, anchor='w', compound='left')

            w.grid(row=row, column=col, sticky='news')
            widgets.append(w)
            col += 1

        return widgets

    def _onCellChanged(self, widget):
        pass

    def setWidgetEditable(self, w, cb):
        var = tk.StringVar()
        w.config(textvariable=var)
        w.variable = var  #keep ref: widget->var
        self._var_widgets[str(var)] = w  #keep ref: var->widget

        def onEnterEdit(e):
            e.widget.config(state='normal')
            e.widget.focus_set()

        def onLeaveEdit(e):
            if e.widget.cget('state') == 'normal':
                e.widget.config(state='disabled')

        def onEditWrite(*args):
            var_name = args[0]
            widget = self._var_widgets.get(var_name)
            cb(widget)

        w.bind('<Double-Button-1>', onEnterEdit)
        w.bind('<Leave>', onLeaveEdit)
        w.bind('<Return>', onLeaveEdit)
        w.variable.trace_variable('w', onEditWrite)


    def initRowData(self, widgets, row_data):
        col = 0
        for col_hdr in self._col_hdrs:
            type, title, editable = col_hdr

            cell_data = row_data[col]
            w = widgets[col]

            if type == self.COL_TYPE_STR and editable:
                w.variable.set(cell_data)
            elif type == self.COL_TYPE_STR and not editable:
                w.config(text=cell_data)
            elif type == self.COL_TYPE_BOOL:
                text = 'v' if cell_data else 'x'
                color = 'green' if cell_data else 'red'
                w.config(text=text, fg=color)
            elif type == self.COL_TYPE_PIC:
                img = ImageTk.PhotoImage(cell_data)
                w.config(image=img, text='')
                w.image = img  #keep ref

            col += 1

    def TMP(self):
        for w in self._elems:
            row += 1
            on_motion = lambda e: self.onMotion(e)

            #icon
            icon = ImageTk.PhotoImage(conf.getIcon(w.sym))
            icon_label = tk.Label(frame, image=icon, anchor='e')
            icon_label.image=icon
            icon_label.bind('<Motion>', on_motion)
            icon_label.grid(row=row, column=0, sticky='news')

            name_label = tk.Label(frame, text=w.name, font=font, anchor='w')
            name_label.bind('<Motion>', on_motion)
            name_label.grid(row=row, column=1, sticky='news')

            pos_txt = conf.getPtPosText(w, fmt='%.3f\n%.3f')
            pos_label = tk.Label(frame, text=pos_txt, font=font)
            pos_label.bind('<Motion>', on_motion)
            pos_label.grid(row=row, column=2, sticky='news')

            ele_label = tk.Label(frame, text=conf.getPtEleText(w), font=font)
            ele_label.bind('<Motion>', on_motion)
            ele_label.grid(row=row, column=3, sticky='news')

            time_label = tk.Label(frame, text=conf.getPtTimeText(w), font=font)
            time_label.bind('<Motion>', on_motion)
            time_label.grid(row=row, column=4, sticky='news')

            #save
            self.__widgets[w] = (
                    icon_label,
                    name_label,
                    pos_label,
                    ele_label,
                    time_label
            )

    def addRow(self, row_data):
        if len(row_data) != self.cols:
            raise ValueError("The data number is not equal to the column number.")
        self._data.append(tuple(row_data))


class ListEditBoard(Dialog):
    def __init__(self, master, elems, wpt=None):
        super().__init__(master)

        self.__widgets = {}  #wpt: widgets 
        self.__focused_wpt = None
        self.__bg_color = self.cget('bg')
        self.__bg_hl_color = 'lightblue'
        self.init()
                
        #set wpt
        if wpt is not None:
            self.setCurrWpt(wpt)

        #wait
        self.wait_window(self)

    def init(self):
        self.sf = pmw.ScrolledFrame(self, usehullsize = 1, hull_width = 300, hull_height = 600)
        self.sf.pack(fill = 'both', expand = 1)


        frame = self.sf.interior()
        font = self._font
        bfont = self._bold_font

        row = 0
        tk.Label(frame, text=self._title_name, font=bfont).grid(row=row, column=1)
        tk.Label(frame, text=self._title_pos,  font=bfont).grid(row=row, column=2)
        tk.Label(frame, text=self._title_ele,  font=bfont).grid(row=row, column=3)
        tk.Label(frame, text=self._title_time, font=bfont).grid(row=row, column=4)

        for w in self._elems:
            row += 1
            on_motion = lambda e: self.onMotion(e)

            #icon
            icon = ImageTk.PhotoImage(conf.getIcon(w.sym))
            icon_label = tk.Label(frame, image=icon, anchor='e')
            icon_label.image=icon
            icon_label.bind('<Motion>', on_motion)
            icon_label.grid(row=row, column=0, sticky='news')

            name_label = tk.Label(frame, text=w.name, font=font, anchor='w')
            name_label.bind('<Motion>', on_motion)
            name_label.grid(row=row, column=1, sticky='news')

            pos_txt = conf.getPtPosText(w, fmt='%.3f\n%.3f')
            pos_label = tk.Label(frame, text=pos_txt, font=font)
            pos_label.bind('<Motion>', on_motion)
            pos_label.grid(row=row, column=2, sticky='news')

            ele_label = tk.Label(frame, text=conf.getPtEleText(w), font=font)
            ele_label.bind('<Motion>', on_motion)
            ele_label.grid(row=row, column=3, sticky='news')

            time_label = tk.Label(frame, text=conf.getPtTimeText(w), font=font)
            time_label.bind('<Motion>', on_motion)
            time_label.grid(row=row, column=4, sticky='news')

            #save
            self.__widgets[w] = (
                    icon_label,
                    name_label,
                    pos_label,
                    ele_label,
                    time_label
            )

    def getWptOfWidget(self, w):
        for wpt, widgets in self.__widgets.items():
            if w in widgets:
                return wpt
        return None

    def onMotion(self, e):
        prev_wpt = self.__focused_wpt
        curr_wpt = self.getWptOfWidget(e.widget)

        #highligt/unhighlight
        if prev_wpt != curr_wpt:
            if prev_wpt is not None:
                self.unhighlightWpt(prev_wpt)
            if curr_wpt is not None:
                self.highlightWpt(curr_wpt)
                
        #rec
        self.__focused_wpt = curr_wpt

    #override
    def highlightWpt(self, wpt, is_focus=False):
        for w in self.__widgets[wpt]:
            w.config(bg=self.__bg_hl_color)
        super().highlightWpt(wpt)

    #override
    def unhighlightWpt(self, wpt):
        for w in self.__widgets[wpt]:
            w.config(bg=self.__bg_color)
        #super().unhighlightWpt(wpt)  #can skip, deu to followed by highlight

    #override
    def showWptIcon(self, wpt):
        pass

    #override
    def setCurrWpt(self, wpt):
        self._curr = wpt

class SingleEditBoard(Dialog):
    def __init__(self, master, elems, wpt=None):
        super().__init__(master, elems, wpt)

        #change buttons
        self.__left_btn = tk.Button(self, text="<<", command=lambda:self.onWptSelected(-1), disabledforeground='gray')
        self.__left_btn.pack(side='left', anchor='w', expand=0, fill='y')
        self.__right_btn = tk.Button(self, text=">>", command=lambda:self.onWptSelected(1), disabledforeground='gray')
        self.__right_btn.pack(side='right', anchor='e', expand=0, fill='y')

        #info
        self.info_frame = self.getInfoFrame()
        self.info_frame.pack(side='bottom', anchor='sw', expand=0, fill='x')

        #image
        self.__img_label = None
        self.__img_sz = (img_w, img_h) = (600, 450)
        if self._hasPicWpt():
            #bd=0: let widget size align image size; set width/height to disable auto resizing
            self.__img_label = tk.Label(self, bg='black', bd=0, width=img_w, height=img_h)
            self.__img_label.pack(side='top', anchor='nw', expand=1, fill='both', padx=0, pady=0)
            self.__img_label.bind('<Configure>', self.onImageResize)

        #set wpt
        if wpt is None:
            wpt = elems[0]
        self.setCurrWpt(wpt)

        #wait
        self.wait_window(self)

    def onImageResize(self, e):
        if hasattr(self.__img_label, 'image'):
            img_w = self.__img_label.image.width()
            img_h = self.__img_label.image.height()
            #print('event: %d, %d; winfo: %d, %d; label: %d, %d; img: %d, %d' % (e.width, e.height, self.__img_label.winfo_width(), self.__img_label.winfo_height(), self.__img_label['width'], self.__img_label['height'], img_w, img_h))
            if e.width < img_w or e.height < img_h or (e.width > img_w and e.height > img_h):
                #print('need to zomm image')
                self.setWptImg(self._curr)

    def onWptSelected(self, inc):
        idx = self._elems.index(self._curr) + inc
        if idx >= 0 and idx < len(self._elems):
            self.setCurrWpt(self._elems[idx])

    def getInfoFrame(self):
        font = self._font
        bold_font = self._bold_font

        frame = tk.Frame(self)#, bg='blue')

        row = 0
        #set sym rule
        tk.Button(frame, text="Rule...", font=font, relief='groove', overrelief='ridge', command=self.onEditSymRule).grid(row=row, column=0, sticky='w')
        #wpt icon
        self.__icon_label = tk.Label(frame)
        self.__icon_label.grid(row=row, column=1, sticky='e')
        self.__icon_label.bind('<Button-1>', self.onSymClick)

        #wpt name
        name_entry = tk.Entry(frame, textvariable=self._var_name, font=font)
        name_entry.bind('<Return>', lambda e: self.onWptSelected(1))
        name_entry.grid(row=row, column=2, sticky='w')

        row += 1
        #focus
        tk.Checkbutton(frame, text=self._title_focus, variable=self._var_focus).grid(row=row, column=0, sticky='w')
        #wpt positoin
        tk.Label(frame, text=self._title_pos, font=bold_font).grid(row=row, column=1, sticky='e')
        self._var_pos = tk.StringVar()
        tk.Label(frame, font=font, textvariable=self._var_pos).grid(row=row, column=2, sticky='w')

        row +=1
        #ele
        tk.Label(frame, text=self._title_ele, font=bold_font).grid(row=row, column=1, sticky='e')
        self._var_ele = tk.StringVar()
        tk.Label(frame, font=font, textvariable=self._var_ele).grid(row=row, column=2, sticky='w')

        row +=1
        #time
        tk.Label(frame, text=self._title_time, font=bold_font).grid(row=row, column=1, sticky='e')
        self._var_time = tk.StringVar()
        tk.Label(frame, textvariable=self._var_time, font=font).grid(row=row, column=2, sticky='w')

        return frame

    def onSymClick(self, e):
        wpt = self._curr
        sym = askSym(self, pos=(e.x_root, e.y_root), init_sym=wpt.sym)

        if sym is not None and sym != wpt.sym:
            wpt.sym = sym
            self._is_changed = True
            self.showWptIcon(wpt)

            #update map
            self.onAltered('wpt')
            self.highlightWpt(wpt)

    def showWptIcon(self, wpt):
        icon = ImageTk.PhotoImage(conf.getIcon(wpt.sym))
        self.__icon_label.image = icon
        self.__icon_label.config(image=icon, text=wpt.sym, compound='right')

    def setWptImg(self, wpt):
        img_w = self.__img_label

        if img_w is None:
            return
        size = self.__img_sz if not hasattr(img_w, 'image') else (img_w.winfo_width(), img_w.winfo_height())
        img = getAspectResize(wpt.img, size) if isinstance(wpt, PicDocument) else getTextImag("(No Pic)", size)
        img = ImageTk.PhotoImage(img)
        img_w.config(image=img)
        img_w.image = img #keep a ref

    def setCurrWpt(self, wpt):
        if self._curr != wpt:
            self.unhighlightWpt(self._curr)
            self.highlightWpt(wpt)

        self._curr = wpt

        #title
        self.title(wpt.name)

        #set imgae
        self.setWptImg(wpt)

        #info
        self.showWptIcon(wpt)
        self._var_name.set(wpt.name)   #this have side effect to set symbol icon
        self._var_pos.set(conf.getPtPosText(wpt))
        self._var_ele.set(conf.getPtEleText(wpt))
        self._var_time.set(conf.getPtTimeText(wpt))

        #button state
        if self._elems is not None:
            idx = self._elems.index(wpt)
            sz = len(self._elems)
            self.__left_btn.config(state=('disabled' if idx == 0 else 'normal'))
            self.__right_btn.config(state=('disabled' if idx == sz-1 else 'normal'))


if __name__ == '__main__':
    import conf

    root = tk.Tk()

    hdr1 = (EditBoard.COL_TYPE_BOOL, 'COL1', True)
    hdr2 = (EditBoard.COL_TYPE_PIC, 'COL2', False)
    hdr3 = (EditBoard.COL_TYPE_STR, 'COL3', True)
    hdr4 = (EditBoard.COL_TYPE_STR, 'COL4', False)
    hdrs = (hdr1, hdr2, hdr3, hdr4)

    brd = EditBoard(root, hdrs)
    brd.addClosedHandler(lambda: print('I am on closed'))
    brd.addRow((True, conf.getIcon('summit'), 'Editable Str', 'UnEditable Str'))
    brd.title('I am Dialog')
    brd.show()

    #root.mainloop()

