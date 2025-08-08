import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
from PIL import Image, ImageTk, ImageOps
import csv

class ImagePointPicker:

    def __init__(self, root):
        self.root = root
        root.title("文献图片数据采集")
        # 初始化变量
        self.image_path = None
        self.photo = None
        self.canvas_img = None
        self.img_area = None
        self.points = []
        self.point_ids = []
        self.mag_photo = None
        self.current_mouse_pos = (0, 0)
        self.target_idx = None
        self.keys = {'coord_mod':False,'point_mod':False}
        self.e_0 = [0.0,0.0]
        self.e_coord = [0.0,0.0]
        self.e_x = [1.0,0.0]
        self.e_y = [0.0,1.0]
        
        # 创建界面
        self.create_widgets()
        # 放大镜更新定时器
        self.update_magnifier()
        
    
    def create_widgets(self):
        self.root.rowconfigure(0,minsize=10)
        self.root.rowconfigure(1,minsize=500)
        self.root.rowconfigure(2,minsize=100)
        self.root.rowconfigure(3,minsize=10)
        self.root.columnconfigure(0,minsize=10)
        self.root.columnconfigure(2,minsize=10)
        self.root.columnconfigure(4,minsize=10)
        self.root.columnconfigure(6,minsize=10)
        self.toolbar = tk.Frame(self.root)
        self.toolbar.grid(row=1,column=1,sticky='n')
        self.name = tk.Label(self.toolbar, text='①',font=('微软雅黑',12)).pack(anchor='nw')
        self.btn_load = tk.Button(self.toolbar, text="导入图片", command=self.load_image,width=10)
        self.btn_load.pack(padx=5, pady=2)
        self.name = tk.Label(self.toolbar, text=' ').pack(anchor='nw')
        self.name = tk.Label(self.toolbar, text='②',font=('微软雅黑',12)).pack(anchor='nw')
        self.btn_load = tk.Button(self.toolbar, text="默认坐标系", command=self.reset_coord,width=10)
        self.btn_load.pack(padx=5, pady=2)
        self.btn_load = tk.Button(self.toolbar, text="自定坐标系", command=self.start_coord,width=10)
        self.btn_load.pack(padx=5, pady=2)
        self.name = tk.Label(self.toolbar, text=' ').pack(anchor='nw')
        self.name = tk.Label(self.toolbar, text='③',font=('微软雅黑',12)).pack(anchor='nw')
        self.btn_load = tk.Button(self.toolbar, text="开始/重新\n取点", command=self.start_point,width=10)
        self.btn_load.pack(padx=5, pady=2)
        self.name = tk.Label(self.toolbar, text=' ').pack(anchor='nw')
        self.name = tk.Label(self.toolbar, text='④',font=('微软雅黑',12)).pack(anchor='nw')
        self.btn_save = tk.Button(self.toolbar, text="保存数据", command=self.save_to_csv,width=10)
        self.btn_save.pack(padx=5, pady=2)

        self.mag_frame = tk.Frame(self.root)
        self.mag_frame.grid(row=2,column=1,sticky='S')
        self.mag_canvas = tk.Canvas(self.mag_frame, width=100, height=100,
                                   highlightbackground='black', highlightthickness=1)
        self.mag_canvas.pack()
        self.mag_canvas.create_line(50, 0, 50, 100, fill='red', tags='crosshair')
        self.mag_canvas.create_line(0, 50, 100, 50, fill='red', tags='crosshair')
        self.main_frame = tk.Frame(self.root)
        self.main_frame.grid(row=1,column=3,rowspan=2)
        self.canvas = tk.Canvas(self.main_frame, width=800, height=600, bg='white')
        self.canvas.grid(row=0,column=0)

        self.tree = ttk.Treeview(self.root, columns=("ID", "X", "Y"), show="headings",height=29)
        self.tree.heading("ID", text="序号")
        self.tree.heading("X", text="X坐标")
        self.tree.heading("Y", text="Y坐标")
        self.tree.column("ID", width=50)
        self.tree.column("X", width=100)
        self.tree.column("Y", width=100)
        self.tree.grid(row=1,column=5,rowspan=2,sticky='N')
        
        self.status = tk.StringVar()
        self.statusbar = tk.Label(self.root, textvariable=self.status, bd=1)
        self.statusbar.grid(row=4,column=3,sticky='s')

        self.current = tk.StringVar()
        # self.current.set('☞ 导入图片')
        self.update_keys()
        self.currentbar = tk.Label(self.root, textvariable=self.current, bd=1)
        self.currentbar.grid(row=4,column=1,sticky='ws')
        
        # 绑定事件
        self.on_left_click()
        self.on_right_click()
        self.release_right_click()
        self.canvas.bind("<Motion>", self.update_status)
        self.root.resizable(False,False)

    def on_left_click(self):
        if self.keys['coord_mod']:
            self.canvas.bind("<Button-1>", self.add_coord_point)
        if self.keys['point_mod']:
            self.canvas.bind("<Button-1>", self.add_point)

    def on_right_click(self):
        if self.keys['coord_mod']:
            self.canvas.bind("<Button-3>", self.remove_coord_point)
        if self.keys['point_mod']:
            self.canvas.bind("<Button-3>", self.remove_point_pre)
        
    def release_right_click(self):
        if self.keys['point_mod']:
            self.canvas.bind("<ButtonRelease-3>", self.remove_point)

    def load_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp,*.gif,*.tiff,*.tif")])
        if not path:
            return
        
        # 清除旧数据
        self.canvas.delete("all")
        self.points.clear()
        self.point_ids.clear()
        self.tree.delete(*self.tree.get_children())
        
        # 加载并调整图片大小
        img = Image.open(path)
        # 处理图像方向的手动实现
        try:
            exif = img._getexif()
        except Exception:
            exif = None

        orientation_key = 274  # 这是EXIF的Orientation标签代码
        if exif and orientation_key in exif:
            orientation = exif[orientation_key]
            
            # 根据Orientation值进行转换
            if orientation == 3:
                img = img.rotate(180, expand=True)
            elif orientation == 6:
                img = img.rotate(270, expand=True)
            elif orientation == 8:
                img = img.rotate(90, expand=True)
        # 其他Orientation值可根据需要补充
        
        # 计算缩放比例
        canvas_width = 800 * 0.96  # 两边各2%边距
        canvas_height = 600 * 0.96
        width_ratio = canvas_width / img.width
        height_ratio = canvas_height / img.height
        scale = min(width_ratio, height_ratio)
        
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.LANCZOS)
        
        # 在画布中央显示图片
        self.photo = ImageTk.PhotoImage(img)
        x = (800 - new_size[0]) // 2
        y = (600 - new_size[1]) // 2
        self.canvas_img = self.canvas.create_image(x, y, anchor=tk.NW, image=self.photo,tags='img')
        
        # 保存图片位置信息
        self.img_area = (x, y, x+new_size[0], y+new_size[1])
        self.scaled_img = img  # 保存缩放后的PIL图像对象
        self.keys = {'coord_mod':False,'point_mod':True}
        self.start_point()

    def reset_coord(self):
        if not self.img_area:
            return
        self.points.clear()
        self.point_ids.clear()
        self.canvas.delete("axis")
        self.canvas.delete("coord")
        self.canvas.delete("node")
        self.e_0 = [0.0,0.0]
        self.e_coord = [0.0,0.0]
        self.e_x = [1.0,0.0]
        self.e_y = [0.0,1.0]
        self.tree.delete(*self.tree.get_children())
        self.keys['coord_mod']=False
        self.keys['point_mod']=True

    def start_coord(self):
        if not self.img_area:
            return
        self.reset_coord()
        self.keys['coord_mod']=True
        self.keys['point_mod']=False
        self.on_left_click()
        self.on_right_click()
        self.tree.delete(*self.tree.get_children())

    def add_coord_point(self, event):
        if not self.img_area:
            return
        if not self.keys['coord_mod']:
            return
        
        if len(self.points)<3:
            point_name = ["原点", "X轴终点", "Y轴终点"][len(self.points)]
            x, y = event.x, event.y
            point_id = self.canvas.create_oval(x-4, y-4, x+4, y+4,fill='red', outline='red',tags='coord')
            coords = self.input_coord_point(point_name,point_id)
            if coords:
                self.points.append(
                                    {'canvas_id':point_id,
                                    'name':point_name,
                                    'x':x,
                                    'y':y,
                                    'coord_x':coords[0],
                                    'coord_y':coords[1]}
                                    )
            else:
                return
            if len(self.points)==3:
                self.canvas.unbind("<Button-1>")
                self.canvas.unbind("<Button-3>")
                self.canvas.delete("axis")
                self.canvas.delete("coord")
                d=0
                if self.points[2]['y']>self.points[0]['y']:
                    d=0
                
                self.canvas.create_line(
                                        self.points[0]['x'], self.points[0]['y'], 
                                        self.points[1]['x'], self.points[1]['y'], 
                                        fill='blue', arrow=tk.LAST, width=3,
                                        tags="axis"
                                        )
                
                self.canvas.create_line(
                                        self.points[0]['x'], self.points[0]['y'],
                                        self.points[2]['x'], self.points[2]['y'], 
                                        fill='green', arrow=tk.LAST,width=3, 
                                        tags="axis"
                                        )
                self.canvas.create_text(
                                        self.points[0]['x'], self.points[0]['y']+d,
                                        text=f'({self.points[0]["coord_x"]}, {self.points[0]["coord_y"]})', 
                                        fill='red', font=('Arial',10), 
                                        tags="axis"
                                        )
                self.canvas.create_text(
                                        self.points[1]['x'], self.points[1]['y']+d,
                                        text=f'({self.points[1]["coord_x"]}, {self.points[1]["coord_y"]})', 
                                        fill='red', font=('Arial',10), 
                                        tags="axis"
                                        )
                self.canvas.create_text(
                                        self.points[2]['x'], self.points[2]['y']-d,
                                        text=f'({self.points[2]["coord_x"]}, {self.points[2]["coord_y"]})', 
                                        fill='red', font=('Arial',10), 
                                        tags="axis"
                                        )
                try:
                    length_x=((self.points[1]['coord_x']-self.points[0]['coord_x'])**2
                              +(self.points[1]['coord_y']-self.points[0]['coord_y'])**2)**0.5
                    length_y=((self.points[2]['coord_x']-self.points[0]['coord_x'])**2
                              +(self.points[2]['coord_y']-self.points[0]['coord_y'])**2)**0.5
                    self.e_x=[(self.points[1]['x']-self.points[0]['x'])/length_x,
                              (self.points[1]['y']-self.points[0]['y'])/length_x]
                    self.e_y=[(self.points[2]['x']-self.points[0]['x'])/length_y,
                              (self.points[2]['y']-self.points[0]['y'])/length_y]
                    self.e_0=[self.points[0]['x'],self.points[0]['y']]
                    self.e_coord=[self.points[0]['coord_x'],self.points[0]['coord_y']]
                    self.points.clear()
                    self.keys['coord_mod']=False
                    self.keys['point_mod']=True
                    self.start_point()
                except:
                    messagebox.showerror("错误", "坐标输入有误")
                    self.start_coord()

    def input_coord_point(self, point_name,point_id):
        tmp="0.0, 0.0"
        if len(self.points)==1:
            tmp="1.0, 0.0"
        if len(self.points)==2:
            tmp="0.0, 1.0"
        s = simpledialog.askstring("输入坐标", f"请输入 {point_name} 的坐标 (x,y):", initialvalue=tmp)
        if not s:
            self.canvas.delete(point_id)
            return None
        try:
            x, y = map(float, s.split(','))
            return (x, y)
        except:
            messagebox.showerror("错误", "输入格式错误，请使用 'x,y' 格式")
            self.canvas.delete(point_id)
            return None


    def remove_coord_point(self, event):
        if not self.points:
            return
        if self.keys['coord_mod']:
        # 执行删除操
            self.canvas.delete(self.points[-1]['canvas_id'])
            del self.points[-1]

    def start_point(self):
        if not self.img_area:
            return
        self.keys['coord_mod']=False
        self.keys['point_mod']=True
        self.on_left_click()
        self.on_right_click()
        self.release_right_click()
        self.points.clear()
        self.point_ids.clear()
        self.tree.delete(*self.tree.get_children())
        self.canvas.delete("node")

    def add_point(self, event):
        if not self.img_area:
            return
        
        # 检查是否在图片区域内
        x, y = event.x, event.y
            
        # 绘制点
        try:
            point_id = self.canvas.create_oval(x-4, y-4, x+4, y+4,fill='yellow', outline='blue',tags='node')
            self.point_ids.append(point_id)
            coord=Point_Coord(x,y).tran_coord(self.e_0,self.e_x,self.e_y,self.e_coord)
            self.points.append({'canvas_id':point_id,'x':x,'y':y,'coord_x':coord[0],'coord_y':coord[1]})
            
            # 更新表格
            self.tree.insert("", "end", values=(len(self.points),"{:.6e}".format(coord[0]), "{:.6e}".format(coord[1])))
        except:
            messagebox.showerror('错误','自定义坐标系有误，已恢复默认。\n如需要，请重新定义。')
            self.reset_coord()

    def remove_point_pre(self, event):
        if not self.points:
            return

        threshold = 10
        min_dist = float('inf')
        self.target_idx = None
            # 遍历所有点寻找最近点
        for idx, point in enumerate(self.points):
            dx = event.x - point['x']
            dy = event.y - point['y']
            distance = (dx**2 + dy**2)**0.5  # 计算欧几里得距离
            
            if distance < threshold and distance < min_dist:
                min_dist = distance
                self.target_idx = idx
        if self.target_idx is not None:
            x, y = self.points[self.target_idx]['x'], self.points[self.target_idx]['y']
            self.canvas.create_oval(x-5, y-5, x+5, y+5, outline='red', width=2, tags='temp')
            
        return self.target_idx

    def remove_point(self, event):
        if not self.points:
            return
        threshold = 10
        # 执行删除操作
        if self.target_idx is not None:
            dx = event.x - self.points[self.target_idx]['x']
            dy = event.y - self.points[self.target_idx]['y']
            distance = (dx**2 + dy**2)**0.5
            if distance<threshold:
                

                self.canvas.delete(self.points[self.target_idx]['canvas_id'])
                del self.points[self.target_idx]
                self.rebuild_table()
            
            self.canvas.after(100, lambda: self.canvas.delete('temp'))
            
            
            # 重建表格（自动更新所有序号）
            
            self.target_idx = None

    def rebuild_table(self):
        
        self.tree.delete(*self.tree.get_children())  # 清空现有数据

        for idx, point in enumerate(self.points, start=1):
            self.tree.insert("", "end", values=(idx, "{:.6e}".format(point['x']), "{:.6e}".format(point['y'])))

    def update_keys(self):
        line='☞ 导入图片'
        if not self.img_area:
            line='☞ 导入图片'
        else:
            if self.keys['coord_mod']:
                line='☞ 自定坐标系'
            if self.keys['point_mod']:
                line='☞ 图片取点中'
        self.current.set(line)
        self.root.after(500, self.update_keys)

    def update_status(self, event):

        self.status.set(f"( {event.x}, {event.y} )")
        self.current_mouse_pos = (event.x, event.y)

    def update_magnifier(self):
        if hasattr(self, 'scaled_img') and self.img_area:
            x, y = self.current_mouse_pos
                
            # 转换为图片坐标
            img_x = x - self.img_area[0]
            img_y = y - self.img_area[1]
            
            # 截取周边区域
            size = 10  # 原始区域大小
            try:
                box = (
                    max(0, img_x-size), 
                    max(0, img_y-size),
                    min(self.scaled_img.width, img_x+size),
                    min(self.scaled_img.height, img_y+size)
                )
                region = self.scaled_img.crop(box)
                
                # 放大5倍
                a=(box[2]-box[0])*5
                b=(box[3]-box[1])*5
                if box[1]<=0:
                    px=100
                    py=100
                    pos=tk.SE
                else:
                    px=0
                    py=0
                    pos=tk.NW
                if box[0]<=0:
                    px=100
                    py=100
                    pos=tk.SE
                    if box[1]<=0:
                        px=100
                        py=100
                        pos=tk.SE
                    if box[3]>=self.scaled_img.height:
                        px=100
                        py=0
                        pos=tk.NE
                if box[2]>=self.scaled_img.width:
                    px=0
                    py=0
                    pos=tk.NW
                    if box[1]<=0:
                        px=0
                        py=100
                        pos=tk.SW
                    if box[3]>=self.scaled_img.height:
                        px=0
                        py=0
                        pos=tk.NW
                if a>0 and b>0:

                    region = region.resize((a, b), Image.NEAREST)
                    self.mag_photo = ImageTk.PhotoImage(region)
                    self.mag_canvas.delete("all")
                    self.mag_canvas.create_image(px, py, anchor=pos, image=self.mag_photo)
                    self.mag_canvas.create_line(50, 0, 50, 100, fill='red', tags='crosshair')
                    self.mag_canvas.create_line(0, 50, 100, 50, fill='red', tags='crosshair')
            except Exception as e:
                print("放大镜更新错误:", e)

        self.root.after(33, self.update_magnifier)  # ~30Hz更新频率

    def save_to_csv(self):
        if not self.points:
            return
        
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv")]
        )
        if path:
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "X", "Y"])
                for i, point in enumerate(self.points, 1):
                    writer.writerow([i, point['coord_x'], point['coord_y']])

class Point_Coord:
    def __init__(self,rx,ry):
        self.x=rx
        self.y=ry

    def tran_coord(self,e_0=[0.0,0.0],e_x=[1.0,0.0],e_y=[0.0,1.0],e_coord=[0.0,0.0]):
        tmp=e_x[0]*e_y[1]-e_y[0]*e_x[1]
        mat=[[e_y[1]/tmp,-e_y[0]/tmp],
             [-e_x[1]/tmp,e_x[0]/tmp]]
        res=[e_coord[0]+mat[0][0]*(self.x-e_0[0])+mat[0][1]*(self.y-e_0[1]),
             e_coord[1]+mat[1][0]*(self.x-e_0[0])+mat[1][1]*(self.y-e_0[1])]
        return res


if __name__ == "__main__":
    root = tk.Tk()
    app = ImagePointPicker(root)
    root.mainloop()