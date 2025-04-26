import numpy as np
import sys
import os
import time
from plcm import ImageEncryptionSystem
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from Crypto.Random import get_random_bytes

# Thêm thư mục chứa plcm.py vào sys.path
sys.path.insert(0, '/Users/linhha/C++/encrypt_video')

def to_binary_string(data):
    """Chuyển dữ liệu thành chuỗi binary (0 và 1)"""
    if isinstance(data, np.ndarray):
        data = data.tobytes()
    return ''.join(format(byte, '08b') for byte in data)

def binary_string_to_bytes(binary_str):
    """Chuyển chuỗi binary (0 và 1) thành bytes"""
    if not binary_str:
        return b''
    
    # Đảm bảo độ dài chuỗi chia hết cho 8
    padded_str = binary_str
    if len(binary_str) % 8 != 0:
        padded_str = binary_str + '0' * (8 - len(binary_str) % 8)
    
    return bytes(int(padded_str[i:i+8], 2) for i in range(0, len(padded_str), 8))

def encrypt_with_AES_CBC(data, key):
    """Mã hóa dữ liệu bằng AES (CBC mode)"""
    if isinstance(data, np.ndarray):
        data = data.tobytes()
    cipher = AES.new(key, AES.MODE_CBC)
    iv = cipher.iv
    padded_data = pad(data, AES.block_size)
    ciphertext = cipher.encrypt(padded_data)
    return iv + ciphertext

def encrypt_with_plcm(binary_data, system):
    """Mã hóa chuỗi binary bằng PLCM"""
    # Chuyển chuỗi binary thành mảng NumPy uint8
    print("Chuyển đổi chuỗi binary thành mảng...")
    data_bytes = binary_string_to_bytes(binary_data)
    data_array = np.frombuffer(data_bytes, dtype=np.uint8)
    
    # Tính toán kích thước ma trận 2D
    length = len(data_array)
    height = int(np.sqrt(length)) 
    width = (length + height - 1) // height  # Đảm bảo width*height >= length
    
    print(f"Dữ liệu đầu vào: {length} byte -> Ma trận {height}x{width}")
    
    # Đệm dữ liệu nếu cần và reshape thành ma trận 2D, not sure
    if length < height * width:
        padding_length = height * width - length
        print(f"Đệm thêm {padding_length} byte cho đủ kích thước ma trận")
        data_array = np.pad(data_array, (0, padding_length), mode='constant')
    
    data_2d = data_array.reshape(height, width)
    
    # Cập nhật thông tin cho hệ thống mã hóa
    print("Chuẩn bị hệ thống mã hóa...")
    system.image = data_2d.astype(np.uint8)
    system.height, system.width = height, width
    
    # Cập nhật các frame trung gian, sử dụng thuộc tính trực tiếp của system
    if hasattr(system, 'temp_frame'):
        system.temp_frame = np.zeros_like(data_2d)
    if hasattr(system, 'confused_frame'):
        system.confused_frame = np.zeros_like(data_2d)
    if hasattr(system, 'diffused_frame'):
        system.diffused_frame = np.zeros_like(data_2d)
    
    # Mã hóa dữ liệu
    print("Tiến hành mã hóa...")
    encrypted = system.encrypt()
    
    # Chuyển kết quả thành chuỗi binary
    print("Chuyển đổi kết quả mã hóa thành chuỗi binary...")
    return to_binary_string(encrypted.flatten())

def bits_to_mbits(bits):
    """Chuyển đổi từ bit sang Megabit"""
    return bits / (1024 * 1024)

def main():
    # Đường dẫn file chuỗi binary đầu vào
    if len(sys.argv) > 1:
        binary_file = sys.argv[1]
    else:
        binary_file = input("Nhập đường dẫn file chuỗi binary (.txt): ")

    # Kiểm tra file tồn tại
    if not os.path.exists(binary_file):
        raise FileNotFoundError(f"File chuỗi binary {binary_file} không tồn tại")

    # Đọc chuỗi binary từ file
    print(f"Đang đọc chuỗi binary từ file: {binary_file}")
    read_start_time = time.time()
    
    # Đọc file theo chunks để xử lý file lớn
    with open(binary_file, 'r') as file:
        chunk_size = 10 * 1024 * 1024  # 10MB mỗi chunk
        binary_data = ""
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            binary_data += chunk.strip()
    
    read_time = time.time() - read_start_time
    data_size_bits = len(binary_data)  # Kích thước chuỗi binary (bit)
    data_size_mbits = bits_to_mbits(data_size_bits)  # Kích thước chuỗi binary (Mbit)
    
    print(f"Thời gian đọc chuỗi binary: {read_time:.2f} giây")
    print(f"Kích thước chuỗi binary: {data_size_bits:,} bit ({data_size_mbits:.2f} Mbit)")

    # --- Mã hóa bằng PLCM ---
    print(f"\nBắt đầu mã hóa chuỗi binary bằng PLCM...")
    plcm_start_time = time.time()

    try:
        # Khởi tạo ImageEncryptionSystem với kích thước phù hợp
        # Chọn kích thước ban đầu dựa trên kích thước dữ liệu
        dummy_size = min(1024, max(8, int(np.sqrt(data_size_bits/8))))
        dummy_image = np.zeros((dummy_size, dummy_size), dtype=np.uint8)
        
        print(f"Khởi tạo ImageEncryptionSystem với kích thước ban đầu {dummy_size}x{dummy_size}")
        system = ImageEncryptionSystem(dummy_image)
        
        # Mã hóa dữ liệu
        encrypted_plcm_binary = encrypt_with_plcm(binary_data, system)
        
        # Tính thời gian và tốc độ
        plcm_total_time = time.time() - plcm_start_time
        plcm_bitrate = data_size_bits / plcm_total_time if plcm_total_time > 0 else 0
        plcm_mbitrate = bits_to_mbits(plcm_bitrate)
        
        print(f"\nHoàn thành mã hóa PLCM!")
        print(f"Tổng thời gian PLCM: {plcm_total_time:.2f} giây")
        print(f"Tốc độ mã hóa PLCM: {plcm_mbitrate:.2f} Mb/s")
        
    except Exception as e:
        import traceback
        print(f"Lỗi trong quá trình mã hóa PLCM: {e}")
        traceback.print_exc()
        print("Bỏ qua mã hóa PLCM và chuyển sang AES-CBC...")
        encrypted_plcm_binary = ""
        plcm_total_time = 0
        plcm_mbitrate = 0

    # --- Mã hóa bằng AES-CBC ---
    print(f"\nBắt đầu mã hóa chuỗi binary bằng AES-CBC...")
    aes_start_time = time.time()

    # Tạo khóa AES (256-bit)
    key = get_random_bytes(32)
    
    # Chuyển chuỗi binary thành bytes và mã hóa
    print("Chuyển đổi chuỗi binary thành bytes...")
    data_bytes = binary_string_to_bytes(binary_data)
    
    print("Mã hóa dữ liệu với AES-CBC...")
    encrypted_aes = encrypt_with_AES_CBC(data_bytes, key)
    
    print("Chuyển đổi kết quả mã hóa thành chuỗi binary...")
    encrypted_aes_binary = to_binary_string(encrypted_aes)

    # Tính thời gian và tốc độ
    aes_total_time = time.time() - aes_start_time
    aes_bitrate = data_size_bits / aes_total_time if aes_total_time > 0 else 0
    aes_mbitrate = bits_to_mbits(aes_bitrate)
    
    print(f"\nHoàn thành mã hóa AES-CBC!")
    print(f"Tổng thời gian AES-CBC: {aes_total_time:.2f} giây")
    print(f"Tốc độ mã hóa AES-CBC: {aes_mbitrate:.2f} Mb/s")

    # --- So sánh ---
    if plcm_total_time > 0:
        print(f"\nSo sánh tốc độ mã hóa:")
        print(f"PLCM: {plcm_mbitrate:.2f} Mb/s")
        print(f"AES-CBC: {aes_mbitrate:.2f} Mb/s")
        if plcm_mbitrate > aes_mbitrate:
            print(f"PLCM nhanh hơn AES-CBC khoảng {(plcm_mbitrate / aes_mbitrate):.2f} lần")
        else:
            print(f"AES-CBC nhanh hơn PLCM khoảng {(aes_mbitrate / plcm_mbitrate):.2f} lần")

    # Ghi kết quả ra file nếu có
    if encrypted_plcm_binary:
        output_file = f"PLCM_re_encrypted_{os.path.basename(binary_file)}"
        print(f"\nĐang ghi kết quả PLCM vào file: {output_file}")
        
        # Ghi file theo chunks để xử lý file lớn
        with open(output_file, 'w') as file:
            chunk_size = 10 * 1024 * 1024  # 10MB mỗi chunk
            for i in range(0, len(encrypted_plcm_binary), chunk_size):
                file.write(encrypted_plcm_binary[i:i+chunk_size])

    output_file_aes = f"AES_CBC_re_encrypted_{os.path.basename(binary_file)}"
    print(f"Đang ghi kết quả AES-CBC vào file: {output_file_aes}")
    
    # Ghi file theo chunks để xử lý file lớn
    with open(output_file_aes, 'w') as file:
        chunk_size = 10 * 1024 * 1024  # 10MB mỗi chunk
        for i in range(0, len(encrypted_aes_binary), chunk_size):
            file.write(encrypted_aes_binary[i:i+chunk_size])

if __name__ == "__main__":
    main()
