import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import threading
import os
import cv2
import sys
from defocus.defocus import DefocuserObject

class DefudeGuiTk:
    def __init__(self, checkpoint_path):
        self.checkpoint_path = checkpoint_path
        self.root = tk.Tk()
        self.root.title("Synthetic Defocusing and Depth Estimation Tool")
        self.root.geometry("1000x800")
        
        # State variables
        self.input_image_path = None
        self.depth_map_path = None
        self.defocus_image_path = None
        self.input_image_size = None
        self.gui_image_size = (600, int(600 * 0.75)) # default aspect ratio
        
        self.setup_ui()

    def setup_ui(self):
        # Create a notebook (tabs) to replace the Gtk Stack
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)
        
        # --- TAB 1: Select Image ---
        self.tab_select = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_select, text="Select Image")
        
        lbl_inst = ttk.Label(self.tab_select, text="Please select an input image", font=('Arial', 14))
        lbl_inst.pack(pady=20)
        
        btn_select = ttk.Button(self.tab_select, text="Browse Image...", command=self.on_select_image)
        btn_select.pack(pady=10)
        
        self.lbl_image_preview = ttk.Label(self.tab_select)
        self.lbl_image_preview.pack(pady=10, expand=True)
        
        self.btn_next_1 = ttk.Button(self.tab_select, text="Estimate Depth Map ->", command=self.on_estimate_depth, state=tk.DISABLED)
        self.btn_next_1.pack(pady=20)

        # --- TAB 2: Processing / Depth Map ---
        self.tab_depth = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_depth, text="Depth Map", state="disabled")
        
        self.lbl_status_depth = ttk.Label(self.tab_depth, text="Estimating Depth Map... Please wait.", font=('Arial', 14))
        self.lbl_status_depth.pack(pady=20)
        
        self.lbl_depth_preview = ttk.Label(self.tab_depth)
        self.lbl_depth_preview.pack(pady=10, expand=True)
        
        frame_depth_actions = ttk.Frame(self.tab_depth)
        frame_depth_actions.pack(pady=20)
        
        self.btn_save_depth = ttk.Button(frame_depth_actions, text="Save Depth Map", command=lambda: self.save_image(self.depth_map_path), state=tk.DISABLED)
        self.btn_save_depth.pack(side=tk.LEFT, padx=10)
        
        self.btn_next_2 = ttk.Button(frame_depth_actions, text="Pick Point of Focus ->", command=self.on_goto_focus, state=tk.DISABLED)
        self.btn_next_2.pack(side=tk.LEFT, padx=10)
        
        # --- TAB 3: Pick Focus ---
        self.tab_focus = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_focus, text="Pick Focus", state="disabled")
        
        lbl_focus_inst = ttk.Label(self.tab_focus, text="Click anywhere on the image to pick a point of focus.", font=('Arial', 14))
        lbl_focus_inst.pack(pady=20)
        
        self.lbl_focus_image = ttk.Label(self.tab_focus)
        self.lbl_focus_image.pack(pady=10, expand=True)
        self.lbl_focus_image.bind("<Button-1>", self.on_image_click)
        
        # --- TAB 4: Final Result ---
        self.tab_result = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_result, text="Result", state="disabled")
        
        self.lbl_status_result = ttk.Label(self.tab_result, text="Applying defocus... Please wait.", font=('Arial', 14))
        self.lbl_status_result.pack(pady=20)

        self.lbl_result_preview = ttk.Label(self.tab_result)
        self.lbl_result_preview.pack(pady=10, expand=True)
        
        frame_result_actions = ttk.Frame(self.tab_result)
        frame_result_actions.pack(pady=20)

        self.btn_save_result = ttk.Button(frame_result_actions, text="Save Result", command=lambda: self.save_image(self.defocus_image_path), state=tk.DISABLED)
        self.btn_save_result.pack(side=tk.LEFT, padx=10)
        
        self.btn_restart = ttk.Button(frame_result_actions, text="Start Over", command=self.on_restart)
        self.btn_restart.pack(side=tk.LEFT, padx=10)

    def load_and_resize_image(self, path, width=600):
        img = Image.open(path)
        w, h = img.size
        ar = h / float(w)
        new_h = int(width * ar)
        img = img.resize((width, new_h), Image.LANCZOS)
        return ImageTk.PhotoImage(img), (width, new_h)

    def on_select_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")])
        if file_path:
            self.input_image_path = file_path
            photo, size = self.load_and_resize_image(file_path)
            self.gui_image_size = size
            self.input_image_size = size
            
            self.lbl_image_preview.configure(image=photo)
            self.lbl_image_preview.image = photo
            self.btn_next_1.config(state=tk.NORMAL)

    def _estimate_depth_impl(self):
        os.system(f'"{sys.executable}" ./depth/depth_simple.py --checkpoint_path "{self.checkpoint_path}" --image_path "{self.input_image_path}"')
        self.depth_map_path = os.path.join(os.path.dirname(self.input_image_path), os.path.basename(self.input_image_path).split('.')[0] + '_disp.png')
        
        # Update UI from main thread
        self.root.after(0, self._on_depth_done)

    def _on_depth_done(self):
        photo, _ = self.load_and_resize_image(self.depth_map_path)
        self.lbl_depth_preview.configure(image=photo)
        self.lbl_depth_preview.image = photo
        
        self.lbl_status_depth.config(text="Depth Map Estimated Successfully!")
        self.btn_save_depth.config(state=tk.NORMAL)
        self.btn_next_2.config(state=tk.NORMAL)

    def on_estimate_depth(self):
        self.notebook.tab(self.tab_depth, state="normal")
        self.notebook.select(self.tab_depth)
        self.lbl_status_depth.config(text="Estimating Depth Map... Please wait.")
        self.btn_save_depth.config(state=tk.DISABLED)
        self.btn_next_2.config(state=tk.DISABLED)
        
        threading.Thread(target=self._estimate_depth_impl, daemon=True).start()

    def on_goto_focus(self):
        self.notebook.tab(self.tab_focus, state="normal")
        self.notebook.select(self.tab_focus)
        
        photo, _ = self.load_and_resize_image(self.input_image_path)
        self.lbl_focus_image.configure(image=photo)
        self.lbl_focus_image.image = photo

    def on_image_click(self, event):
        x, y = event.x, event.y
        x_norm = x / self.gui_image_size[0]
        y_norm = y / self.gui_image_size[1]
        
        self.notebook.tab(self.tab_result, state="normal")
        self.notebook.select(self.tab_result)
        self.lbl_status_result.config(text="Applying defocus... Please wait.")
        self.btn_save_result.config(state=tk.DISABLED)
        
        threading.Thread(target=self._defocus_impl, args=(x_norm, y_norm), daemon=True).start()

    def _defocus_impl(self, x_norm, y_norm):
        defocuser = DefocuserObject(self.input_image_path)
        
        # Override imshow and imwrite to not pop up OpenCV windows
        original_imshow = cv2.imshow
        cv2.imshow = lambda *args, **kwargs: None
        
        defocuser.set_pof_from_coord(x_norm, y_norm)
        
        # Restore imshow
        cv2.imshow = original_imshow
        
        self.defocus_image_path = os.path.join(os.path.dirname(self.input_image_path), os.path.basename(self.input_image_path).split('.')[0] + '_defocus.png')
        
        # Update UI from main thread
        self.root.after(0, self._on_defocus_done)

    def _on_defocus_done(self):
        photo, _ = self.load_and_resize_image(self.defocus_image_path)
        self.lbl_result_preview.configure(image=photo)
        self.lbl_result_preview.image = photo
        
        self.lbl_status_result.config(text="Defocus Applied! Click below to save or pick another focus.")
        self.btn_save_result.config(state=tk.NORMAL)

    def save_image(self, source_path):
        if not source_path or not os.path.exists(source_path):
            messagebox.showerror("Error", "No image to save!")
            return
            
        dest_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
        if dest_path:
            img = cv2.imread(source_path)
            cv2.imwrite(dest_path, img)
            messagebox.showinfo("Success", "Image saved successfully!")

    def on_restart(self):
        self.notebook.select(self.tab_select)
        self.notebook.tab(self.tab_depth, state="disabled")
        self.notebook.tab(self.tab_focus, state="disabled")
        self.notebook.tab(self.tab_result, state="disabled")

    def show(self):
        self.root.mainloop()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--model_path', type=str, required=True)
    parser.add_argument('--image_path', type=str, help='(Ignored by GUI)', default='')
    parser.add_argument('--blur_method', type=str, help='(Ignored by GUI)', default='')
    args, unknown = parser.parse_known_args()
    
    gui = DefudeGuiTk(os.path.abspath(args.model_path))
    gui.show()
