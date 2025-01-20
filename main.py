from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.list import OneLineListItem, MDList
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.properties import ObjectProperty
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivymd.uix.textfield import MDTextField
import os
import shutil
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image
from kivy.uix.camera import Camera
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image as KivyImage
from kivy.clock import Clock

Builder.load_file("output_compiler.kv")

class MenuScreen(Screen):
    pass

class FolderScreen(Screen):
    pass

class CameraScannerScreen(Screen):
    pass

class OutputCompilerApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.file_manager = None
        self.selected_files = []
        self.last_directory = os.path.expanduser("~")  # Start from home directory
        self.dialog = None
        self.output_folder = "OutputCompiler"
        self.folder_paths = {}
        self.scanned_files = []

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        
        # Initialize file manager
        self.file_manager = MDFileManager(
            exit_manager=self.close_file_manager,
            select_path=self.select_file,
            preview=True,
        )
        
        # Create output folder
        self.create_output_folder()
        
        return Builder.load_string(KV)

    def create_output_folder(self):
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

    def open_file_manager(self):
        self.file_manager.show(self.last_directory)

    def close_file_manager(self, *args):
        self.file_manager.close()

    def select_file(self, path):
        self.last_directory = os.path.dirname(path)
        if os.path.isfile(path):
            if path not in self.selected_files:
                self.show_folder_selection_dialog(path)
            else:
                self.show_dialog("Error", f"File {os.path.basename(path)} is already added.")
        self.file_manager.close()

    def show_dialog(self, title, text):
        def dismiss_dialog(*args):
            if self.dialog:
                self.dialog.dismiss()
                self.dialog = None

        if self.dialog:
            self.dialog.dismiss()
        
        self.dialog = MDDialog(
            title=title,
            text=text,
            buttons=[
                MDRaisedButton(
                    text="OK",
                    on_release=dismiss_dialog
                )
            ]
        )
        self.dialog.open()

    def show_folder_selection_dialog(self, file_path):
        if not self.folder_paths:
            self.show_dialog("Error", "Please create a folder first")
            return

        def dismiss_dialog(*args):
            if self.dialog:
                self.dialog.dismiss()
                self.dialog = None

        if self.dialog:
            self.dialog.dismiss()

        buttons = []
        for folder_name in self.folder_paths:
            buttons.append(
                MDRaisedButton(
                    text=folder_name,
                    on_release=lambda x, fn=folder_name: self.add_file_to_folder(file_path, fn)
                )
            )

        self.dialog = MDDialog(
            title="Select Folder",
            text="Choose a folder to add the file to:",
            buttons=buttons
        )
        self.dialog.open()

    def add_file_to_folder(self, file_path, folder_name):
        try:
            folder_path = self.folder_paths[folder_name]
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            
            file_name = os.path.basename(file_path)
            destination = os.path.join(folder_path, file_name)
            
            shutil.copy2(file_path, destination)
            self.selected_files.append(destination)
            
            if self.dialog:
                self.dialog.dismiss()
                self.dialog = None
            
            self.update_file_list()
            self.show_dialog("Success", f"File added to {folder_name}")
            
        except Exception as e:
            self.show_dialog("Error", f"Failed to add file: {str(e)}")

    def update_file_list(self):
        file_list = self.root.get_screen('menu').ids.file_list
        file_list.clear_widgets()
        for file_path in self.selected_files:
            file_list.add_widget(
                OneLineListItem(text=os.path.basename(file_path))
            )

    def create_folder(self):
        folder_name = self.root.get_screen('folder').ids.new_folder_name.text.strip()
        if not folder_name:
            self.show_dialog("Error", "Please enter a folder name")
            return
            
        folder_path = os.path.join(self.output_folder, folder_name)
        if os.path.exists(folder_path):
            self.show_dialog("Error", "Folder already exists")
            return
            
        try:
            os.makedirs(folder_path)
            self.folder_paths[folder_name] = folder_path
            self.update_folder_list()
            self.root.get_screen('folder').ids.new_folder_name.text = ""
            self.show_dialog("Success", f"Folder '{folder_name}' created")
        except Exception as e:
            self.show_dialog("Error", f"Failed to create folder: {str(e)}")

    def update_folder_list(self):
        folder_list = self.root.get_screen('folder').ids.folder_list
        folder_list.clear_widgets()
        for folder_name in sorted(self.folder_paths.keys()):
            folder_list.add_widget(
                OneLineListItem(text=folder_name)
            )

    def capture_image(self):
        camera = self.root.get_screen('scanner').ids.camera
        if not camera.texture:
            self.show_dialog("Error", "Camera not ready")
            return
            
        timestamp = Clock.get_time()
        image_path = os.path.join(self.output_folder, f"scan_{timestamp}.png")
        camera.export_to_png(image_path)
        
        if os.path.exists(image_path):
            self.show_folder_selection_dialog(image_path)
        else:
            self.show_dialog("Error", "Failed to capture image")

    def compile_to_pdf(self):
        if not self.selected_files:
            self.show_dialog("Error", "No files selected")
            return
            
        try:
            output_pdf = os.path.join(self.output_folder, "compiled_output.pdf")
            merger = PdfWriter()
            
            for file_path in self.selected_files:
                if file_path.lower().endswith('.pdf'):
                    pdf = PdfReader(file_path)
                    for page in pdf.pages:
                        merger.add_page(page)
                elif file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                    img = Image.open(file_path)
                    img_pdf = os.path.join(self.output_folder, "temp.pdf")
                    img.save(img_pdf, "PDF")
                    pdf = PdfReader(img_pdf)
                    merger.append_pages_from_reader(pdf)
                    os.remove(img_pdf)
            
            with open(output_pdf, "wb") as output_file:
                merger.write(output_file)
            
            self.show_dialog("Success", f"PDF compiled successfully: {output_pdf}")
            
        except Exception as e:
            self.show_dialog("Error", f"Failed to compile PDF: {str(e)}")

    def change_screen(self, screen_name):
        self.root.current = screen_name

if __name__ == "__main__":
    OutputCompilerApp().run()