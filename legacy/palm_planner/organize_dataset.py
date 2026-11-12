import os
import shutil
import random
from pathlib import Path

def organize_yolo_dataset(source_folder, output_folder, train_ratio=0.7, val_ratio=0.2, test_ratio=0.1):
    """
    Organize dataset from LabelImg format to proper YOLO structure
    
    Args:
        source_folder: Folder berisi gambar dan label dari LabelImg
        output_folder: Folder output untuk struktur YOLO
        train_ratio: Rasio data training (0-1)
        val_ratio: Rasio data validation (0-1) 
        test_ratio: Rasio data testing (0-1)
    """
    
    # Validasi rasio
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 0.01, "Rasio harus berjumlah 1.0"
    
    # Buat folder struktur YOLO
    folders = [
        'images/train', 'images/val', 'images/test',
        'labels/train', 'labels/val', 'labels/test'
    ]
    
    for folder in folders:
        os.makedirs(os.path.join(output_folder, folder), exist_ok=True)
        print(f"Created folder: {folder}")
    
    # Dapatkan semua file gambar
    image_extensions = ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']
    image_files = []
    
    for file in os.listdir(source_folder):
        if any(file.lower().endswith(ext) for ext in image_extensions):
            image_files.append(file)
    
    print(f"Found {len(image_files)} image files")
    
    # Acak urutan file
    random.shuffle(image_files)
    
    # Hitung jumlah untuk setiap split
    total_files = len(image_files)
    train_count = int(total_files * train_ratio)
    val_count = int(total_files * val_ratio)
    test_count = total_files - train_count - val_count
    
    # Split dataset
    train_files = image_files[:train_count]
    val_files = image_files[train_count:train_count + val_count]
    test_files = image_files[train_count + val_count:]
    
    print(f"\nDataset Split:")
    print(f"Training: {len(train_files)} images")
    print(f"Validation: {len(val_files)} images") 
    print(f"Testing: {len(test_files)} images")
    
    # Fungsi untuk menyalin file
    def copy_split_files(file_list, split_name):
        copied_count = 0
        missing_labels = 0
        
        for image_file in file_list:
            # Salin gambar
            image_src = os.path.join(source_folder, image_file)
            image_dst = os.path.join(output_folder, 'images', split_name, image_file)
            shutil.copy2(image_src, image_dst)
            
            # Salin file label
            label_name = os.path.splitext(image_file)[0] + '.txt'
            label_src = os.path.join(source_folder, label_name)
            label_dst = os.path.join(output_folder, 'labels', split_name, label_name)
            
            if os.path.exists(label_src):
                shutil.copy2(label_src, label_dst)
                copied_count += 1
            else:
                print(f"Warning: Label file not found for {image_file}")
                missing_labels += 1
        
        return copied_count, missing_labels
    
    # Salin file untuk setiap split
    print("\nCopying files...")
    
    train_copied, train_missing = copy_split_files(train_files, 'train')
    val_copied, val_missing = copy_split_files(val_files, 'val') 
    test_copied, test_missing = copy_split_files(test_files, 'test')
    
    # Buat file dataset.yaml
    create_dataset_yaml(output_folder)
    
    print(f"\n✅ Dataset organized successfully!")
    print(f"Training: {train_copied} images ({(train_copied/len(train_files))*100:.1f}% with labels)")
    print(f"Validation: {val_copied} images ({(val_copied/len(val_files))*100:.1f}% with labels)")
    print(f"Testing: {test_copied} images ({(test_copied/len(test_files))*100:.1f}% with labels)")
    
    if train_missing + val_missing + test_missing > 0:
        print(f"⚠️  Total missing labels: {train_missing + val_missing + test_missing}")

def create_dataset_yaml(dataset_path):
    """Create YOLO dataset configuration file"""
    
    yaml_content = f"""# Palm Tree Detection Dataset
path: {os.path.abspath(dataset_path)}
train: images/train
val: images/val
test: images/test

# Number of classes
nc: 1

# Class names
names: ['palm_tree']

# Dataset information
description: Palm tree detection dataset from satellite imagery
created: {os.path.basename(dataset_path)}
version: 1.0
"""
    
    yaml_file = os.path.join(dataset_path, 'palm_trees.yaml')
    with open(yaml_file, 'w') as f:
        f.write(yaml_content)
    
    print(f"Created dataset config: {yaml_file}")

def validate_dataset(dataset_path):
    """Validate the organized dataset"""
    
    print(f"\n🔍 Validating dataset structure...")
    
    required_folders = [
        'images/train', 'images/val', 'images/test',
        'labels/train', 'labels/val', 'labels/test'
    ]
    
    # Check folder structure
    for folder in required_folders:
        full_path = os.path.join(dataset_path, folder)
        if not os.path.exists(full_path):
            print(f"❌ Missing folder: {folder}")
            return False
        else:
            file_count = len([f for f in os.listdir(full_path) if not f.startswith('.')])
            print(f"✅ {folder}: {file_count} files")
    
    # Check label files match image files
    for split in ['train', 'val', 'test']:
        images_path = os.path.join(dataset_path, 'images', split)
        labels_path = os.path.join(dataset_path, 'labels', split)
        
        image_files = [f for f in os.listdir(images_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        label_files = [f for f in os.listdir(labels_path) if f.endswith('.txt')]
        
        # Check if every image has a corresponding label
        missing_labels = []
        for img_file in image_files:
            label_name = os.path.splitext(img_file)[0] + '.txt'
            if label_name not in label_files:
                missing_labels.append(img_file)
        
        if missing_labels:
            print(f"❌ {split}: {len(missing_labels)} images missing labels")
            for missing in missing_labels[:5]:  # Show first 5
                print(f"   - {missing}")
        else:
            print(f"✅ {split}: All images have corresponding labels")
    
    return True

if __name__ == "__main__":
    # Contoh penggunaan
    source_folder = "path/to/your/labelimg/folder"  # Ganti dengan path folder LabelImg Anda
    output_folder = "datasets/palm_trees"
    
    if not os.path.exists(source_folder):
        print(f"❌ Source folder not found: {source_folder}")
        print("Please update the source_folder path in the script")
    else:
        organize_yolo_dataset(source_folder, output_folder)
        validate_dataset(output_folder)