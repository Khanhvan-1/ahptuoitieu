from django.core.management.base import BaseCommand
from irrigation.models import Garden
import random

class Command(BaseCommand):
    help = "Tạo dữ liệu 40 vườn cà phê với tên thật và vị trí đa dạng trên Đắk Lắk"

    def handle(self, *args, **kwargs):
        if Garden.objects.exists():
            self.stdout.write(self.style.WARNING("⚠️ Đã có dữ liệu Garden. Dùng 'python manage.py flush' nếu muốn xóa hết để tạo mới."))
            return

        # Danh sách 40 tên vườn chính xác
        farm_names = [
            "Vườn cà phê Ea Tu", "Vườn cà phê Cư Êbur", "Vườn cà phê Hòa Thuận", "Vườn cà phê Ea Kao",
            "Vườn cà phê Hòa Phú", "Vườn cà phê Cư M'gar", "Vườn cà phê Quảng Phú", "Vườn cà phê Ea Ktur",
            "Vườn cà phê Ea Ning", "Vườn cà phê Krông Ana", "Vườn cà phê Krông Pắk", "Vườn cà phê Ea Kênh",
            "Vườn cà phê Ea Yông", "Vườn cà phê Ea H'leo", "Vườn cà phê Dliê Yang", "Vườn cà phê Ea Wy",
            "Vườn cà phê Ea Tir", "Vườn cà phê Ea Hiao", "Vườn cà phê Ea Sol", "Vườn cà phê Ea Tul",
            "Vườn cà phê Krông Búk", "Vườn cà phê Pơng Drang", "Vườn cà phê Ea Drông", "Vườn cà phê Ea H'đing",
            "Vườn cà phê Cư Bao", "Vườn cà phê Ea Siên", "Vườn cà phê Ea Blang", "Vườn cà phê Ea Drăng",
            "Vườn cà phê Ea Khal", "Vườn cà phê M'Drắk", "Vườn cà phê Krông Jing", "Vườn cà phê Cư Prao",
            "Vườn cà phê Ea Riêng", "Vườn cà phê Ea M'Doal", "Vườn cà phê Ea Lai", "Vườn cà phê Krông Á",
            "Vườn cà phê Cư Króa", "Vườn cà phê Ea Trang", "Vườn cà phê Krông Nô", "Vườn cà phê Cư San"
        ]

        # Danh sách các huyện/thị xã/thành phố tại Đắk Lắk (kèm tọa độ trung tâm gần đúng)
        locations = [
            {"name": "Buôn Ma Thuột", "lat": 12.6662, "lng": 108.0383},
            {"name": "Cư M'gar", "lat": 12.7766, "lng": 108.0814},
            {"name": "Krông Ana", "lat": 12.5314, "lng": 108.0842},
            {"name": "Krông Pắk", "lat": 12.6933, "lng": 108.2972},
            {"name": "Ea H'leo", "lat": 13.2333, "lng": 108.1000},
            {"name": "M'Drắk", "lat": 12.7000, "lng": 108.7667},
            {"name": "Krông Nô", "lat": 12.3764, "lng": 107.8897},
            {"name": "Ea Súp", "lat": 13.1667, "lng": 107.8000},
            {"name": "Ea Kar", "lat": 12.8167, "lng": 108.5333},
            {"name": "Krông Bông", "lat": 12.5167, "lng": 108.4667},
            {"name": "Lắk", "lat": 12.4167, "lng": 108.2000},
            {"name": "Cư Kuin", "lat": 12.5500, "lng": 108.0500},
        ]

        for i, name in enumerate(farm_names):
            # Chọn location ngẫu nhiên trong danh sách, nhưng đảm bảo phân bố đều
            loc = locations[i % len(locations)]
            # Tạo tọa độ lệch nhẹ xung quanh trung tâm huyện
            lat = loc["lat"] + random.uniform(-0.05, 0.05)
            lng = loc["lng"] + random.uniform(-0.05, 0.05)
            # Diện tích từ 0.8 đến 4.5 ha
            area = round(random.uniform(0.8, 4.5), 2)

            Garden.objects.create(
                name=name,
                latitude=round(lat, 6),
                longitude=round(lng, 6),
                area=area,
                location=loc["name"]
            )

        self.stdout.write(self.style.SUCCESS(f"✅ Đã tạo {len(farm_names)} vườn cà phê trên khắp Đắk Lắk"))