from django.core.management.base import BaseCommand
from irrigation.models import Garden
import random


class Command(BaseCommand):
    help = "Tạo dữ liệu 40 vườn cà phê"

    def handle(self, *args, **kwargs):
        if Garden.objects.exists():
            self.stdout.write(self.style.WARNING("⚠️ Đã có dữ liệu Garden rồi"))
            return

        farm_names = [
            "Vườn cà phê Ea Tu", "Vườn cà phê Cư Êbur", "Vườn cà phê Ea Kao", "Vườn cà phê Tân Lập",
            "Vườn cà phê Hòa Thắng", "Vườn cà phê Hòa Phú", "Vườn cà phê Ea Tam", "Vườn cà phê Ea Bar",
            "Vườn cà phê Krông Ana", "Vườn cà phê Ea Ning"
        ]

        lat_base = 12.65
        lng_base = 108.05

        for i in range(40):
            name = farm_names[i % len(farm_names)] + f" #{i+1}"

            Garden.objects.create(
                name=name,
                latitude=lat_base + random.uniform(-0.08, 0.08),
                longitude=lng_base + random.uniform(-0.08, 0.08),
                area=round(random.uniform(0.8, 3.5), 2),
                location="Buôn Ma Thuột"
            )

        self.stdout.write(self.style.SUCCESS("✅ Đã tạo 40 vườn thành công"))