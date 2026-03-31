from django.db import models

class WeatherData(models.Model):
    """Dữ liệu thời tiết từ Excel"""
    time = models.DateTimeField(unique=True)
    temperature = models.FloatField(verbose_name='Nhiệt độ (°C)')
    humidity = models.FloatField(verbose_name='Độ ẩm không khí (%)')
    rain = models.FloatField(verbose_name='Lượng mưa (mm)')
    radiation = models.FloatField(verbose_name='Bức xạ (MJ/m²)')
    et0 = models.FloatField(null=True, blank=True, verbose_name='Bốc thoát hơi nước (mm/ngày)')
    soil_moisture = models.FloatField(null=True, blank=True, verbose_name='Độ ẩm đất (%)')
    
    def __str__(self):
        return f"{self.time.strftime('%Y-%m-%d %H:%M')} - T: {self.temperature}°C"


class AHPWeights(models.Model):
    """Trọng số AHP cho các tiêu chí"""
    criterion_choices = [
        ('C1', 'Độ ẩm đất'),
        ('C2', 'Lượng mưa'),
        ('C3', 'Bốc thoát hơi nước ET₀'),
        ('C4', 'Nhiệt độ'),
        ('C5', 'Độ ẩm không khí'),
        ('C6', 'Nắng/gió mùa khô'),
    ]
    
    criterion = models.CharField(max_length=2, choices=criterion_choices, unique=True)
    weight = models.FloatField(verbose_name='Trọng số')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Trọng số AHP'
        verbose_name_plural = 'Trọng số AHP'
    
    def __str__(self):
        return f"{self.get_criterion_display()}: {self.weight}"


class AlternativeScore(models.Model):
    """Điểm số của các phương án tưới"""
    alternative_choices = [
        ('PA1', 'Phương án 1'),
        ('PA2', 'Phương án 2'),
        ('PA3', 'Phương án 3'),
        ('PA4', 'Phương án 4'),
    ]
    
    criterion_choices = [
        ('C1', 'Độ ẩm đất'),
        ('C2', 'Lượng mưa'),
        ('C3', 'Bốc thoát hơi nước ET₀'),
        ('C4', 'Nhiệt độ'),
        ('C5', 'Độ ẩm không khí'),
        ('C6', 'Nắng/gió mùa khô'),
    ]
    
    alternative = models.CharField(max_length=3, choices=alternative_choices)
    criterion = models.CharField(max_length=2, choices=criterion_choices)
    score = models.FloatField(verbose_name='Điểm số')
    
    class Meta:
        unique_together = ['alternative', 'criterion']
        verbose_name = 'Điểm phương án'
        verbose_name_plural = 'Điểm các phương án'
    
    def __str__(self):
        return f"{self.alternative} - {self.criterion}: {self.score}"


class IrrigationDecision(models.Model):
    """Quyết định tưới tiêu"""
    decision_time = models.DateTimeField(auto_now_add=True)
    temperature = models.FloatField(verbose_name='Nhiệt độ hiện tại')
    humidity = models.FloatField(verbose_name='Độ ẩm hiện tại')
    rain = models.FloatField(verbose_name='Lượng mưa')
    soil_moisture = models.FloatField(verbose_name='Độ ẩm đất')
    et0 = models.FloatField(verbose_name='ET₀')
    recommended_action = models.CharField(max_length=20, verbose_name='Hành động khuyến nghị')
    score_pa1 = models.FloatField(null=True, blank=True)
    score_pa2 = models.FloatField(null=True, blank=True)
    score_pa3 = models.FloatField(null=True, blank=True)
    score_pa4 = models.FloatField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.decision_time} - {self.recommended_action}"

class Garden(models.Model):
    """Thông tin 40 vườn cà phê"""
    name = models.CharField(max_length=100, verbose_name="Tên vườn")
    latitude = models.FloatField(verbose_name="Vĩ độ")
    longitude = models.FloatField(verbose_name="Kinh độ")
    area = models.FloatField(default=1.0, verbose_name="Diện tích (ha)")
    location = models.CharField(max_length=255, blank=True, null=True, verbose_name="Khu vực")

    def __str__(self):
        return self.name


class GardenRealtime(models.Model):
    """Dữ liệu realtime cho từng vườn"""
    garden = models.ForeignKey(Garden, on_delete=models.CASCADE, related_name="realtime_data")
    time = models.DateTimeField(auto_now=True)

    temperature = models.FloatField(verbose_name='Nhiệt độ (°C)')
    humidity = models.FloatField(verbose_name='Độ ẩm không khí (%)')
    rain = models.FloatField(verbose_name='Lượng mưa (mm)')
    radiation = models.FloatField(verbose_name='Bức xạ (MJ/m²)')
    et0 = models.FloatField(default=0, verbose_name='Bốc thoát hơi nước (mm/ngày)')
    soil_moisture = models.FloatField(default=0, verbose_name='Độ ẩm đất')

    ai_score = models.FloatField(default=0, verbose_name="Độ tin cậy AI")
    ai_status = models.CharField(max_length=50, blank=True, null=True, verbose_name="Khuyến nghị AI")

    def __str__(self):
        return f"{self.garden.name} - {self.time.strftime('%d/%m/%Y %H:%M:%S')}"