#!/usr/bin/env python3

import tkinter as tk
import Pmw as pmw
import platform
import logging
from PIL import ImageTk
from tkinter import ttk, messagebox
#from utile import MapDescriptor

class Dialog(tk.Toplevel):
    FOCUSOUT_NOOP = 0
    FOCUSOUT_HIDE = 1
    FOCUSOUT_CLOSE = 2

    @property
    def pos(self):
        return self.__pos

    @pos.setter
    def pos(self, v):
        self.__pos = v
        self.geometry('+%d+%d' % v)

    @property
    def focusout_act(self):
        return self.__focusout_act

    @focusout_act.setter
    def focusout_act(self, v):
        self.__focusout_act = v

    def __init__(self, master):
        super().__init__(master)

        self.__focusout_act = self.FOCUSOUT_NOOP

        #handler
        #self._handlers = {}

        #board
        self.pos = (0, 0)
        self.protocol('WM_DELETE_WINDOW', lambda: self._onClosed(None))
        self.bind('<Escape>', self._onClosed)

        #silent update
        self.withdraw()  #hidden
        self._visible = tk.BooleanVar(value=False)

    def show(self, pos=None, has_title=True):
        if pos is not None:
            self.pos = pos

        if self.__focusout_act != self.FOCUSOUT_NOOP:
            self.__bindFocusout(has_title)

        self.overrideredirect(not has_title)

        #UI
        self.transient(self.master)  #remove max/min buttons
        
        self.update()  #update window size

        self.deiconify() #show
        self._visible.set(True)

        #self.attributes("-topmost", 1) #topmost
        self.lift()
        self.focus_set()  #prevent key-press sent back to parent
        self.grab_set()   #disalbe interact of parent
        self.master.wait_variable(self._visible)

    def hidden(self):
        if self.master is not None:
            self.master.focus_set()
        self.grab_release()

        self.withdraw()
        self._visible.set(False)

    def close(self):
        self.hidden()
        self.destroy()

    def _onClosed(self, e):
        self.close()

    def __bindFocusout(self, has_title):
        def on_focusout(e):
            if self == e.widget:
                self.__doFocusoutAction()

        self.bind('<FocusOut>', on_focusout)
        #focusout is not work if overrideredirect set, using enter/leave as workaround
        if not has_title:
            self.bind('<Leave>', on_focusout)

    def __doFocusoutAction(self):
        if self.__focusout_act == self.FOCUSOUT_HIDE:
            logging.debug("dialog is focus out, hidden...")
            self.hidden()
        elif self.__focusout_act == self.FOCUSOUT_CLOSE:
            logging.debug("dialog is focus out, closing...")
            self.close()


    '''
    #{{ handler
    def invokeHandler(self, name):
        if name in self._handlers:
            self._handlers[name]()

    def addClosedHandler(self, h): self._handlers['closed'] = h;
    def onClosed(self): self.invokeHandler('closed')
    #}} handler
    '''

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

class MapRow(tk.Frame):
    ALPHA_MIN = 1
    ALPHA_MAX = 100
    @property
    def map_desc(self):
        return self.__map_desc

    def __init__(self, master, map_desc, alpha_handler=None, enable_handle=None):
        super().__init__(master)

        FONT = "Arialuni 12"
        BFONT = FONT + " bold"

        self.__alpha_handler = alpha_handler
        self.__enable_handler = enable_handle

        self.__map_desc = map_desc

        cmd = lambda:enable_handle(self) if enable_handle is not None else None
        self.__btn = tk.Button(self, command=self.__onEnableChanged)
        self.__setBtnTxt()
        self.__btn.pack(side='right', anchor='e', expand=0)

        #variable
        alpha = int(map_desc.alpha * 100)
        self.__alpha_var = tk.IntVar(value=alpha)
        self.__alpha_var.trace('w', self.__onAlphaChanged)
        #spin
        alpha_label = tk.Label(self, text="%")
        alpha_label.pack(side='right', anchor='e', expand=0)
        alpha_spin = tk.Spinbox(self, from_=self.ALPHA_MIN, to=self.ALPHA_MAX, width=3, textvariable=self.__alpha_var)
        alpha_spin.pack(side='right', anchor='e', expand=0)
        #sacle
        #alpha_scale = tk.Scale(self, label="Transparency", from_=ALPHA_MIN, to=ALPHA_MAX, orient='horizontal',
                #resolution=1, showvalue=0, variable=self.__alpha_var)
        #alpha_scale.pack(side='right', anchor='e', expand=0, fill='x')

        label = tk.Label(self, text=map_desc.map_title, font=BFONT, anchor='w')
        label.pack(side='left', anchor='w', expand='1', fill='x')

    def __setBtnTxt(self):
        self.__btn['text'] = '-' if self.__map_desc.enabled else '+'

    def __onEnableChanged(self):
        old_val = self.__map_desc.enabled
        new_val = not old_val

        self.__map_desc.enabled = new_val
        self.__setBtnTxt()

        if self.__enable_handler is not None:
            self.__enable_handler(self, old_val)

    def __onAlphaChanged(self, *args):
        old_val = self.__map_desc.alpha

        try:
            #get new value
            raw_val = self.__alpha_var.get()
            if raw_val < self.ALPHA_MIN or raw_val > self.ALPHA_MAX: #only accept valid value
                return
            new_val = raw_val / 100.0

            #update
            if self.__map_desc.alpha != new_val:
                self.__map_desc.alpha = new_val

                if self.__alpha_handler is not None:
                    self.__alpha_handler(self, old_val)
        except Exception as ex:
            logging.warning("get alpha value error: " + str(ex))



class MapSelectFrame(pmw.ScrolledFrame):
    @property
    def map_descriptors(self):
        descs = []
        for row in self.__rows:
            descs.append(row.map_desc)
        return descs

    def __init__(self, master, map_descriptors):
        super().__init__(master, usehullsize=1, hull_width=450, hull_height=600)

        #event handlers
        self.__on_enable_changed_handler = None
        self.__on_alpha_changed_handler = None

        #enabled maps are put at head
        map_descriptors = sorted(map_descriptors, key=lambda desc:desc.enabled, reverse=True)

        #create widgets
        self.__rows = []
        for desc in map_descriptors:
            row = MapRow(self.interior(), desc, self.__onAlphaChanged, self.__onEnableChanged)
            self.__rows.append(row)

        self.__splitor = tk.Frame(self.interior(), bg='darkgray', height=10, border=1)

        #show
        self.__pack()

    def setAlphaHandler(self, h):
        self.__on_alpha_changed_handler = h

    def setEnableHandler(self, h):
        self.__on_enable_changed_handler = h

    def __pack(self):
        show_once = False

        for row in self.__rows:
            if not show_once and not row.map_desc.enabled:
                self.__splitor.pack(side='top', anchor='nw', expand=1, fill='x')
                show_once = True

            row.pack(side='top', anchor='nw', expand=1, fill='x')

    def __unpack(self):
        self.__splitor.pack_forget()
        for row in self.__rows:
            row.pack_forget()

    def __getFirstDisabledRow(self):
        for row in self.__rows:
            if not row.map_desc.enabled:
                return row
        return None

    def __onEnableChanged(self, row, old_val):
        #reorder
        self.__rows.remove(row)
        dst_row = self.__getFirstDisabledRow()
        dst_idx = self.__rows.index(dst_row) if dst_row is not None else len(self.__rows)
        self.__rows.insert(dst_idx, row)

        #pack again
        self.__unpack()
        self.__pack()

        if self.__on_enable_changed_handler is not None:
            self.__on_enable_changed_handler(row.map_desc, old_val)

    def __onAlphaChanged(self, row, old_val):
        if self.__on_alpha_changed_handler is not None:
            self.__on_alpha_changed_handler(row.map_desc, old_val)


class MapSelectDialog(Dialog):

    @property
    def map_descriptors(self):
        return self.__map_sel_frame.map_descriptors

    def __init__(self, master, descs):
        super().__init__(master)

        self.__map_sel_frame = MapSelectFrame(self, descs)
        self.__map_sel_frame.pack(side='top', anchor='nw', expand=0)

    def setEnableHandler(self, h):
        self.__map_sel_frame.setEnableHandler(h)

    def setAlphaHandler(self, h):
        self.__map_sel_frame.setAlphaHandler(h)
        

def testMapSelector():
    import os
    import sys
    sys.path.insert(0, 'src')
    from tile import MapDescriptor

    root = tk.Tk()

    #desc
    map_descs = []
    mapcache = "mapcache"
    for f in os.listdir(mapcache):
        if os.path.splitext(f)[1].lower() == ".xml":
            try:
                desc = MapDescriptor.parseXml(os.path.join(mapcache, f))
                if desc.map_id in ('TM25K_2001',  'JM25K_1921'):
                    desc.enabled = True
                    desc.alpha = 0.75
                map_descs.append(desc)
            except Exception as ex:
                print("parse file '%s' error: %s" % (f, str(ex)))
    map_descs = sorted(map_descs, key=lambda d:d.map_title)

    #show
    dialog = Dialog(root)
    selector = MapSelectFrame(dialog, map_descs)
    selector.pack(side='top', anchor='nw', expand=0)
    dialog.show()

    for desc in selector.map_descriptors:
        print(desc.map_id, desc.alpha, desc.enabled)

    root.mainloop()

if __name__ == '__main__':

    testMapSelector()

    '''
    import conf
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
    '''

