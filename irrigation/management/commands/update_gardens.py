import time
import random
from django.core.management.base import BaseCommand
from irrigation.models import Garden, GardenRealtime
from irrigation.views import ai_predict


class Command(BaseCommand):
    help = "Tự cập nhật dữ liệu 40 vườn mỗi 60 giây"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("🚀 Bắt đầu auto update dữ liệu 40 vườn..."))

        while True:
            gardens = Garden.objects.all()

            if not gardens.exists():
                self.stdout.write(self.style.ERROR("❌ Chưa có dữ liệu Garden trong DB"))
                return

            for garden in gardens:
                latest = GardenRealtime.objects.filter(garden=garden).order_by('-time').first()

                if latest:
                    soil = max(0.08, min(0.65, latest.soil_moisture + random.uniform(-0.03, 0.03)))
                    rain = max(0, latest.rain + random.uniform(-1.0, 1.0))
                    eto = max(1.5, min(6.0, latest.et0 + random.uniform(-0.2, 0.2)))
                    temp = max(20, min(38, latest.temperature + random.uniform(-1.0, 1.0)))
                    humidity = max(35, min(95, latest.humidity + random.uniform(-3, 3)))
                    radiation = max(150, min(1200, latest.radiation + random.uniform(-40, 40)))
                else:
                    soil = round(random.uniform(0.12, 0.55), 3)
                    rain = round(random.uniform(0, 10), 2)
                    eto = round(random.uniform(2, 5), 2)
                    temp = round(random.uniform(24, 35), 2)
                    humidity = round(random.uniform(45, 85), 2)
                    radiation = round(random.uniform(180, 1050), 2)

                score, irrigation_status, proba = ai_predict(
                    soil, rain, eto, temp, humidity, radiation
                )

                GardenRealtime.objects.create(
                    garden=garden,
                    soil_moisture=soil,
                    rain=rain,
                    et0=eto,
                    temperature=temp,
                    humidity=humidity,
                    radiation=radiation,
                    ai_score=score,
                    ai_status=irrigation_status
                )

                self.stdout.write(
                    f"✅ {garden.name} | Soil={soil} | Temp={temp} | AI={irrigation_status}"
                )

            self.stdout.write(self.style.SUCCESS("⏳ Đợi 1 ngày để cập nhật tiếp...\n"))
            time.sleep(60)