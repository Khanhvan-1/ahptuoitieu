import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys
import django

# Thiết lập Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coffee_irrigation.settings')
django.setup()

from irrigation.models import WeatherData, AHPWeights, AlternativeScore

def sync_ahp_weights():
    """Đồng bộ trọng số AHP từ Excel"""
    print("Đang đồng bộ trọng số AHP...")
    
    file_path = os.path.join(os.path.dirname(__file__), 'AHP_TuoiTieu.xlsx')
    
    if not os.path.exists(file_path):
        print(f"⚠️ Không tìm thấy file: {file_path}")
        print("Sử dụng trọng số mặc định từ phân tích AHP...")
        
        # Sử dụng trọng số mặc định
        weights = {
            'C1': 0.266,  # Độ ẩm đất
            'C2': 0.115,  # Lượng mưa
            'C3': 0.265,  # Bốc thoát hơi nước
            'C4': 0.130,  # Nhiệt độ
            'C5': 0.058,  # Độ ẩm không khí
            'C6': 0.166,  # Nắng/gió mùa khô
        }
        
        for criterion, weight in weights.items():
            obj, created = AHPWeights.objects.update_or_create(
                criterion=criterion,
                defaults={'weight': weight}
            )
            print(f"  {'✅ Tạo mới' if created else '🔄 Cập nhật'}: {criterion} = {weight}")
        
        print("✅ Đã đồng bộ trọng số AHP (mặc định)!")
        return
    
    try:
        # Đọc từ file
        df_weights = pd.read_excel(file_path, sheet_name='Weights')
        for _, row in df_weights.iterrows():
            obj, created = AHPWeights.objects.update_or_create(
                criterion=row['Criterion'],
                defaults={'weight': row['Weight']}
            )
            print(f"  {'✅ Tạo mới' if created else '🔄 Cập nhật'}: {row['Criterion']} = {row['Weight']}")
        
        print("✅ Đã đồng bộ trọng số AHP từ file!")
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")

def sync_alternative_scores():
    """Đồng bộ điểm số các phương án"""
    print("Đang đồng bộ điểm số phương án...")
    
    file_path = os.path.join(os.path.dirname(__file__), 'AHP_TuoiTieu.xlsx')
    
    if not os.path.exists(file_path):
        print("Sử dụng điểm số mặc định...")
        scores = {
            'PA1': {'C1': 0.06, 'C2': 0.56, 'C3': 0.05, 'C4': 0.06, 'C5': 0.51, 'C6': 0.05},
            'PA2': {'C1': 0.12, 'C2': 0.26, 'C3': 0.13, 'C4': 0.12, 'C5': 0.28, 'C6': 0.13},
            'PA3': {'C1': 0.26, 'C2': 0.12, 'C3': 0.27, 'C4': 0.26, 'C5': 0.14, 'C6': 0.27},
            'PA4': {'C1': 0.56, 'C2': 0.06, 'C3': 0.56, 'C4': 0.56, 'C5': 0.07, 'C6': 0.56},
        }
        
        for alt, criteria_scores in scores.items():
            for criterion, score in criteria_scores.items():
                obj, created = AlternativeScore.objects.update_or_create(
                    alternative=alt,
                    criterion=criterion,
                    defaults={'score': score}
                )
                print(f"  {'✅ Tạo mới' if created else '🔄 Cập nhật'}: {alt} - {criterion} = {score}")
        
        print("✅ Đã đồng bộ điểm số (mặc định)!")
        return
    
    try:
        df_scores = pd.read_excel(file_path, sheet_name='Scores')
        for _, row in df_scores.iterrows():
            obj, created = AlternativeScore.objects.update_or_create(
                alternative=row['Alternative'],
                criterion=row['Criterion'],
                defaults={'score': row['Score']}
            )
            print(f"  {'✅ Tạo mới' if created else '🔄 Cập nhật'}: {row['Alternative']} - {row['Criterion']} = {row['Score']}")
        
        print("✅ Đã đồng bộ điểm số từ file!")
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")

def sync_weather_data_from_csv():
    """Đồng bộ dữ liệu thời tiết từ CSV"""
    print("Đang đồng bộ dữ liệu thời tiết...")
    
    csv_file = os.path.join(os.path.dirname(__file__), 'irrigation_dataset.csv')
    
    if not os.path.exists(csv_file):
        print(f"⚠️ Không tìm thấy file: {csv_file}")
        return
    
    try:
        df = pd.read_csv(csv_file)
        print(f"📊 Đọc được {len(df)} dòng dữ liệu")
        print(f"📋 Các cột: {list(df.columns)}")
        
        count = 0
        # Tạo ngày giả định (bắt đầu từ ngày 2022-01-01)
        start_date = datetime(2022, 1, 1)
        
        for idx, row in df.iterrows():
            try:
                # Tạo thời gian từ index
                time_val = start_date + timedelta(days=idx)
                
                # Lấy dữ liệu
                soil_moisture = float(row['soil']) if pd.notna(row['soil']) else 0
                rain = float(row['rain']) if pd.notna(row['rain']) else 0
                et0 = float(row['eto']) if pd.notna(row['eto']) else 0
                temp = float(row['temp']) if pd.notna(row['temp']) else 0
                humidity = float(row['humidity']) if pd.notna(row['humidity']) else 0
                radiation = float(row['radiation']) if pd.notna(row['radiation']) else 0
                
                # Lưu vào database
                obj, created = WeatherData.objects.update_or_create(
                    time=time_val,
                    defaults={
                        'temperature': temp,
                        'humidity': humidity,
                        'rain': rain,
                        'radiation': radiation,
                        'et0': et0,
                        'soil_moisture': soil_moisture,
                    }
                )
                count += 1
                
                if (idx + 1) % 500 == 0:
                    print(f"  📈 Đã xử lý {idx+1}/{len(df)} dòng...")
                    
            except Exception as e:
                print(f"  ❌ Lỗi dòng {idx}: {e}")
                continue
        
        print(f"✅ Đã đồng bộ {count} bản ghi thời tiết!")
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Hàm chính chạy đồng bộ"""
    print("=" * 60)
    print("🌱 BẮT ĐẦU ĐỒNG BỘ DỮ LIỆU HỆ THỐNG TƯỚI TIÊU")
    print("=" * 60)
    
    # Hiển thị thông tin thư mục
    print(f"\n📁 Thư mục làm việc: {os.getcwd()}")
    print("📄 Các file dữ liệu:")
    for file in os.listdir('.'):
        if file.endswith(('.xlsx', '.xls', '.csv')):
            size = os.path.getsize(file) / 1024
            print(f"  - {file} ({size:.1f} KB)")
    print()
    
    # 1. Đồng bộ trọng số AHP
    sync_ahp_weights()
    print()
    
    # 2. Đồng bộ điểm số phương án
    sync_alternative_scores()
    print()
    
    # 3. Đồng bộ dữ liệu thời tiết
    sync_weather_data_from_csv()
    print()
    
    print("=" * 60)
    print("✅ HOÀN TẤT ĐỒNG BỘ DỮ LIỆU!")
    print("=" * 60)
    
    # Hiển thị thống kê
    print("\n📊 THỐNG KÊ DỮ LIỆU:")
    print(f"  - Trọng số AHP: {AHPWeights.objects.count()}")
    print(f"  - Điểm số phương án: {AlternativeScore.objects.count()}")
    print(f"  - Dữ liệu thời tiết: {WeatherData.objects.count()}")

if __name__ == "__main__":
    main()