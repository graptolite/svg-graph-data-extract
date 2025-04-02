#!/usr/bin/env python3

'''
SVG Graph Data Extractor | Extract (*approximate*) graph-scaled data from a plotted graph after Inkscape preprocessing for further analysis, replotting etc.
    Copyright (C) 2025 Yingbo Li

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''

from tkinter import *
from PIL import Image,ImageTk
import os
import re
import numpy as np
import pandas as pd

class LinTransform2D():
    # Transform a coordinate space (a) into another (B) given two control points.
    def __init__(self,a0,a1,B0,B1):
        self.a0 = np.array(a0)
        self.a1 = np.array(a1)
        self.B0 = np.array(B0)
        self.B1 = np.array(B1)
        self.a_diff = self.a1 - self.a0
        self.B_diff = self.B1 - self.B0
        self.scale = self.B_diff/self.a_diff
        self.delta = self.B0 - (self.scale * self.a0)
        return
    def transform_function(self):
        f_transform = lambda a : a * self.scale + self.delta
        return f_transform
    def transform(self,a_xy):
        f_transform = self.transform_function()
        return f_transform(a_xy)

def extract_path_coords(path):
    methods = {"m":lambda c0,c1: c0 + c1,
               "v":lambda c0,c1: c0 + np.array([0,c1[0]]),
               "h":lambda c0,c1: c0 + np.array([c1[0],0]),
               "l":lambda c0,c1: c0 + c1,
               "M":lambda c0,c1: c1,
               "V":lambda c0,c1: np.array([c0[0],c1[0]]),
               "H":lambda c0,c1: np.array([c1[0],c0[1]]),
               "L":lambda c0,c1: c1,
               }
    raw_coords_m = re.search("d=\"(.+?)\"",path)
    if raw_coords_m:
        raw_coords = raw_coords_m.group(1).split(" ")
    svg_coords = [np.array([0,0])]
    active_method = methods[raw_coords[0]]
    i = 0
    for item in raw_coords:
        if item in methods:
            active_method = methods[item]
        else:
            current_coords = np.array(item.split(",")).astype(float)
            svg_coords.append(active_method(svg_coords[i],current_coords))
            i += 1
    return np.array(svg_coords[1:])

def extract_coords(svg_file,point_style="",x_axis="linear",y_axis="linear",get_center=False,out_file=None):
    if not out_file:
        out_file = svg_file+".csv"
    with open(svg_file) as infile:
        svg = infile.read()
    alignment_points = [m for m in re.findall(r"<circle[\s\S]+?/>",svg) if "coords=" in m]
    if len(alignment_points) == 0:
        alignment_points = [m for m in re.findall(r"<ellipse[\s\S]+?/>",svg) if "coords=" in m]
    if len(alignment_points)!=2:
        raise ValueError("Exactly 2 alignment point are required but found %u alignment points" % len(alignment_points))
    align_centers = []
    graph_centers = []
    for alignment_point in alignment_points:
        # Identify Svg/SVG coordinates of the alignment points.
        m_svg = re.search(r"cx=\"(.*?)\"[\s\S]*?cy=\"(.*?)\"",alignment_point)
        align_centers.append((m_svg.group(1),m_svg.group(2)))
        # Identify graph coordinates of the alignment points.
        m_graph = re.search(r"coords=\"(.*?),(.*?)\"",alignment_point)
        graph_centers.append((m_graph.group(1),m_graph.group(2)))
    # sort alignment points so p1 is topleft and p2 is bottomright
    # p1 in form [[x_svg,y_svg],
    #             [x_graph   ,y_graph   ]]
    # as numpy array
    p1,p2 = np.array(sorted(zip(align_centers,graph_centers),key=lambda x : x[0][0])).astype(float)
    # Determine transform between svg svg and graph coordinate domain.
    svg_topleft = p1[0,:]
    svg_bottomright = p2[0,:]
    svg_topleft[1] = -svg_topleft[1]
    svg_bottomright[1] = -svg_bottomright[1]
    graph_topleft = p1[1,:]
    graph_bottomright = p2[1,:]
    alignment_points = [svg_topleft,svg_bottomright,
                        graph_topleft,graph_bottomright]
    print(alignment_points)
    for i,p in enumerate(alignment_points[2:]):
        if x_axis == "log":
            print("x")
            p[0] = np.log10(p[0])
        if y_axis == "log":
            print("y")
            p[1] = np.log10(p[1])
        print(p)
        alignment_points[i+2] = p
    transformer = LinTransform2D(*alignment_points)
    # Search for path tags.
    paths = [m_str for m_str in re.findall(r"<path[\s\S]*?/>",svg) if point_style in m_str]
    lines = []
    for path in paths:
        try:
            points = extract_path_coords(path)
            # fix coordinate convention
            points[:,1] = -points[:,1]
            # center
            if get_center:
                points = [points.mean(axis=0)]
            graph_points = np.array([transformer.transform(p) for p in points])
            if x_axis == "linear":
                # scale point to graph coordinates
                graph_scale_points_x = graph_points[:,0]
            elif x_axis == "log":
                graph_scale_points_x = 10**graph_points[:,0]
            else:
                graph_scale_points_x = None
            if y_axis == "linear":
                # scale point to graph coordinates
                graph_scale_points_y = graph_points[:,1]
            elif y_axis == "log":
                graph_scale_points_y = 10**graph_points[:,1]
            else:
                graph_scale_points_y = None
            graph_points = np.dstack((graph_scale_points_x,graph_scale_points_y))[0]
            lines.append(graph_points)
        except AttributeError:
            print("No coords found for " + path)
    try:
        max_line_len = max(map(len,lines))
    except ValueError:
        lines = []
    if len(lines):
        lines_dict = dict()
        for i,l in enumerate(lines):
            if len(l) < max_line_len:
                l = np.append(l,[["",""]]*(max_line_len-len(l)),axis=0)
            lines_dict["x%u" % i] = l[:,0]
            lines_dict["y%u" % i] = l[:,1]
        df = pd.DataFrame(lines_dict)
        df.to_csv(out_file,index=False)
    return len(lines),out_file,transformer

class GUI(Tk):
    def __init__(self):
        super().__init__()
        self.geometry("1000x500")
        self.title("SVG Graph Data Extractor")
        self.inputs_frame = Frame(self,bg="lightgrey",borderwidth=5)
        self.inputs_frame.columnconfigure(0,weight=1)
        self.inputs_frame.columnconfigure(0,weight=3)
        self.inputs_frame.place(relheight=1,relwidth=0.3,relx=0.7,y=0)
        self.l_fname = Label(self.inputs_frame,text="SVG Filepath:",font=("bold"))
        self.fname = Entry(self.inputs_frame)
        axis_options = ["linear","log"]
        self.xaxis_selected = StringVar()
        self.xaxis_selected.set(axis_options[0])
        self.l_xaxis = Label(self.inputs_frame,text="X axis scale:")
        self.xaxis_menu = OptionMenu(self.inputs_frame,self.xaxis_selected,*axis_options)

        self.yaxis_selected = StringVar()
        self.yaxis_selected.set(axis_options[0])
        self.l_yaxis = Label(self.inputs_frame,text="Y axis scale:")
        self.yaxis_menu = OptionMenu(self.inputs_frame,self.yaxis_selected,*axis_options)

        dtype_options = ["point","line"]
        self.dtype_selected = StringVar()
        self.dtype_selected.set(dtype_options[0])
        self.l_dtype = Label(self.inputs_frame,text="Data type:")
        self.dtype_menu = OptionMenu(self.inputs_frame,self.dtype_selected,*dtype_options)

        self.l_style = Label(self.inputs_frame,text="Unique Style Attribute:")
        self.style_input = Entry(self.inputs_frame)

        self.l_fout = Label(self.inputs_frame,text="Output CSV (optional):")
        self.fout_input = Entry(self.inputs_frame)

        self.btn_exec = Button(self.inputs_frame,text="Execute",width=10,height=2,command=self.execute)

        input_widget_list = [self.l_fname,self.fname,
                             self.l_xaxis,self.xaxis_menu,
                             self.l_yaxis,self.yaxis_menu,
                             self.l_dtype,self.dtype_menu,
                             self.l_style,self.style_input,
                             self.l_fout,self.fout_input,
                             self.btn_exec
                             ]
        self.stack_widgets(input_widget_list)

        self.outputs_frame = Frame(self,bg="lightblue",borderwidth=5)
        self.outputs_frame.columnconfigure(0,weight=1)
        self.outputs_frame.columnconfigure(0,weight=3)
        self.outputs_frame.place(relheight=1,relwidth=0.7,relx=0,y=0)

        self.update_idletasks()
        w,h = self.outputs_frame.winfo_width(),self.outputs_frame.winfo_height()
        self.text_width = 0.9*(0.9*w)

        self.l_msg = Label(self.outputs_frame,text="Messages",bg="lightblue")
        self.msg = Canvas(self.outputs_frame,width=0.9*w,height=0.9*h,bg="white")

        output_widget_list = [self.l_msg,self.msg]
        self.stack_widgets(output_widget_list)

        self.update_idletasks()
        wm,hm = self.msg.winfo_width(),self.msg.winfo_height()
        self.text_placeholder = self.msg.create_text(wm/2,hm/2,anchor=CENTER)

        self.protocol("WM_DELETE_WINDOW",self.destroy)
        self.init_msg()
        return
    def init_msg(self):
        self.update_msg("""Graph preprocessing - make sure these steps have been done:
1) Convert the vector graph to Inkscape SVG format.
2) Ungroup everything and make sure no transformations are present.
3) Place two circles or ellipses (i.e. alignment points) that are centered about known coords, and should be relatively far away from each other.
4) Using Inkscape's XML editor, add the attribute `coord` to each alignment point. Set the value of `coord` of each point to the known graph's xy coordinates in the format `<x>,<y>`.
5) Ensure all items of interest are path objects (use the object to path function if necessary).
6) Ensure all path(s)/point(s) of interest are paths with *no smooth nodes*. For circular points, this can be achieved by converting all smooth nodes to corner nodes in Inkscape.
7) Ensure the path(s)/points(s) of interest have a uniquely identifying style attribute e.g. unique fill color.
""")
        return
    def execute(self):
        fname = self.fname.get()
        if fname and not os.path.exists(fname):
            self.update_msg("File",fname,"does not exist")
            return
        xscale = self.xaxis_selected.get()
        yscale = self.yaxis_selected.get()
        dtype = self.dtype_selected.get()
        style = self.style_input.get()
        f_out = self.fout_input.get()
        if f_out and not f_out.endswith(".csv"):
            f_out += ".csv"
        print(fname,xscale,yscale,dtype,style,f_out)
        n,outfile,_ = extract_coords(fname,style,xscale,yscale,True if dtype=="point" else False,f_out)
        self.update_msg(" ".join([str(n),"Geometries with style specification containing",style,"found and extracted to",outfile]))
        return
    def stack_widgets(self,widget_list):
        for i,w in enumerate(widget_list):
            w.grid(column=0,row=0+i)
        return
    def update_msg(self,text):
        self.msg.itemconfig(self.text_placeholder,text=text,width=self.text_width)


if __name__=="__main__":
    root = GUI()
    root.mainloop()

#_,_,t = extract_coords("log_test.svg","#0000ff","log","log")
