from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
import openmeteo_requests
import requests_cache
from retry_requests import retry
import joblib
import numpy as np
from .models import WeatherData, AHPWeights, AlternativeScore, Garden, GardenRealtime
from datetime import datetime
from pathlib import Path
import json
import re
from django.conf import settings
from django.core.cache import cache
from google import genai

gemini_client = genai.Client(api_key=settings.GOOGLE_API_KEY)
# =====================
# HOME
# =====================
def home(request):
    return redirect('login')

# =====================
# LOGIN - ĐÃ SỬA
# =====================
def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if not username or not password:
            messages.error(request, "Vui lòng nhập đầy đủ thông tin")
            return render(request, 'login.html')
        
        # Xác thực user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f"Chào mừng {username} trở lại!")
            return redirect('/about/')
        else:
            messages.error(request, "Sai tài khoản hoặc mật khẩu")
            return render(request, 'login.html')
    
    return render(request, 'login.html')

# =====================
# REGISTER - ĐÃ SỬA
# =====================
def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        # Validate
        if not username or not email or not password:
            messages.error(request, "Vui lòng điền đầy đủ thông tin")
            return render(request, 'register.html')
        
        if password != confirm_password:
            messages.error(request, "Mật khẩu xác nhận không khớp")
            return render(request, 'register.html')
        
        if len(password) < 6:
            messages.error(request, "Mật khẩu phải có ít nhất 6 ký tự")
            return render(request, 'register.html')
        
        # Kiểm tra username tồn tại
        if User.objects.filter(username=username).exists():
            messages.error(request, "Tên đăng nhập đã tồn tại")
            return render(request, 'register.html')
        
        # Kiểm tra email tồn tại
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email đã được sử dụng")
            return render(request, 'register.html')
        
        try:
            # Tạo user mới
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            user.save()
            
            messages.success(request, "Đăng ký thành công! Hãy đăng nhập.")
            return redirect('login')
            
        except Exception as e:
            messages.error(request, f"Có lỗi xảy ra: {str(e)}")
            return render(request, 'register.html')
    
    return render(request, 'register.html')

# =====================
# LOGOUT
# =====================
def user_logout(request):
    logout(request)
    messages.info(request, "Bạn đã đăng xuất thành công")
    return redirect('login')

# =====================
# AI MODEL
# =====================
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "irrigation_ai.pkl"
CHAT_MEMORY = {}

def normalize_text(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\sàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text

def has_any(msg, keywords):
    return any(k in msg for k in keywords)

try:
    model = joblib.load(MODEL_PATH)
    print("✅ AI model loaded:", MODEL_PATH)
    print("📌 Classes của model:", model.classes_)
except Exception as e:
    print("❌ Lỗi load model:", e)
    model = None 

def ai_predict(soil, rain, eto, temp, humidity, radiation):
    if model is None:
        return 0, "Không xác định", {
            "high": 0,
            "medium": 0,
            "low": 0,
            "none": 0
        }

    try:
        X = np.array([[soil, rain, eto, temp, humidity, radiation]])
        pred = model.predict(X)[0]
        proba = model.predict_proba(X)[0]
        classes = model.classes_

        print("📌 AI input:", X)
        print("📌 AI pred:", pred)
        print("📌 AI classes:", classes)
        print("📌 AI proba:", proba)

        proba_dict = {
            "high": 0,
            "medium": 0,
            "low": 0,
            "none": 0
        }

        for i, cls in enumerate(classes):
            cls_str = str(cls).strip().lower()

            if cls_str in ["high", "tưới nhiều", "tuoi nhieu", "nhiều", "nhieu"]:
                proba_dict["high"] = round(float(proba[i]) * 100, 2)
            elif cls_str in ["medium", "tưới vừa", "tuoi vua", "vừa", "vua"]:
                proba_dict["medium"] = round(float(proba[i]) * 100, 2)
            elif cls_str in ["low", "tưới ít", "tuoi it", "ít", "it"]:
                proba_dict["low"] = round(float(proba[i]) * 100, 2)
            elif cls_str in ["none", "không tưới", "khong tuoi", "không", "khong"]:
                proba_dict["none"] = round(float(proba[i]) * 100, 2)

        score = round(float(max(proba)) * 10, 2)

        pred_str = str(pred).strip().lower()

        if pred_str in ["high", "tưới nhiều", "tuoi nhieu", "nhiều", "nhieu"]:
            result = "💧 Tưới nhiều"
        elif pred_str in ["medium", "tưới vừa", "tuoi vua", "vừa", "vua"]:
            result = "💧 Tưới vừa"
        elif pred_str in ["low", "tưới ít", "tuoi it", "ít", "it"]:
            result = "💧 Tưới ít"
        elif pred_str in ["none", "không tưới", "khong tuoi", "không", "khong"]:
            result = "❌ Không tưới"
        else:
            result = f"🤖 AI dự đoán: {pred}"

        return score, result, proba_dict

    except Exception as e:
        print("❌ AI predict lỗi:", e)
        return 0, "Không xác định", {
            "high": 0,
            "medium": 0,
            "low": 0,
            "none": 0
        }
    
def get_latest_garden_data():
    """
    Lấy dữ liệu realtime mới nhất của toàn bộ vườn
    """
    latest_data = []

    gardens = Garden.objects.all()

    for garden in gardens:
        realtime = GardenRealtime.objects.filter(garden=garden).order_by('-time').first()
        if realtime:
            latest_data.append({
                "id": garden.id,
                "name": garden.name,
                "lat": garden.latitude,
                "lng": garden.longitude,
                "soil": realtime.soil_moisture,
                "rain": realtime.rain,
                "eto": realtime.et0,
                "temp": realtime.temperature,
                "humidity": realtime.humidity,
                "radiation": realtime.radiation,
                "score": realtime.ai_score,
                "status": realtime.ai_status or "Không xác định"
            })

    return latest_data

def get_farm_ai_explanation(farm):
    reasons = []

    if farm["soil"] < 0.2:
        reasons.append("độ ẩm đất thấp")
    if farm["rain"] < 1:
        reasons.append("lượng mưa thấp")
    if farm["temp"] > 30:
        reasons.append("nhiệt độ cao")
    if farm["radiation"] > 900:
        reasons.append("bức xạ mạnh")
    if farm["eto"] > 3:
        reasons.append("ETo cao")

    if not reasons:
        return "Điều kiện môi trường đang khá ổn định."

    return "AI phân tích: " + ", ".join(reasons) + "."

def gardens_realtime(request):
    farms = get_latest_garden_data()
    return JsonResponse(farms, safe=False)

@login_required
def dashboard(request):
    try:
        cache_session = requests_cache.CachedSession('.cache', expire_after=15)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        openmeteo = openmeteo_requests.Client(session=retry_session)

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 12.3977,
            "longitude": 108.2181,
            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "rain",
                "wind_speed_10m",
                "shortwave_radiation"
            ],
            "hourly": [
                "temperature_2m",
                "et0_fao_evapotranspiration",
                "soil_moisture_0_to_1cm"
            ],
            "timezone": "Asia/Bangkok"
        }

        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]
        current = response.Current()

        temperature = round(current.Variables(0).Value(), 2)
        humidity = round(current.Variables(1).Value(), 2)
        rain = round(current.Variables(2).Value(), 2)
        wind = round(current.Variables(3).Value(), 2)
        radiation = round(current.Variables(4).Value(), 2)

        hourly = response.Hourly()

        try:
            eto = round(float(hourly.Variables(1).ValuesAsNumpy()[0]), 2)
        except:
            eto = 0

        try:
            soil_moisture = round(float(hourly.Variables(2).ValuesAsNumpy()[0]), 3)
        except:
            soil_moisture = 0

    except Exception as e:
        print("Lỗi dashboard API:", e)

        # fallback dữ liệu mặc định để KHÔNG trắng trang
        temperature = 28
        humidity = 65
        rain = 0
        wind = 3
        radiation = 220
        eto = 3.5
        soil_moisture = 0.28

    try:
        score, irrigation_status, proba = ai_predict(
            soil_moisture, rain, eto, temperature, humidity, radiation
        )
    except Exception as e:
        print("Lỗi AI predict:", e)
        score = 0
        irrigation_status = "Không xác định"
    # ===== AI EXPLANATION =====
    ai_explanation = []

    if soil_moisture < 0.2:
        ai_explanation.append(f"Độ ẩm đất rất thấp ({soil_moisture})")

    if rain == 0:
        ai_explanation.append("Không có mưa gần đây")

    if temperature > 30:
        ai_explanation.append(f"Nhiệt độ cao ({temperature}°C)")

    if radiation > 900:
        ai_explanation.append(f"Bức xạ mạnh ({radiation})")

    if eto > 3:
        ai_explanation.append(f"ETo cao ({eto})")

    if not ai_explanation:
        ai_explanation.append("Điều kiện môi trường ổn định")

    ai_explanation_text = " → ".join(ai_explanation)

        # ===== AI ACTION RECOMMENDATION =====
    if "nhiều" in irrigation_status.lower():
        water_amount = "20 - 25 lít/gốc"
        duration = "20 - 25 phút"
    elif "vừa" in irrigation_status.lower():
        water_amount = "12 - 15 lít/gốc"
        duration = "12 - 15 phút"
    elif "ít" in irrigation_status.lower():
        water_amount = "5 - 8 lít/gốc"
        duration = "5 - 8 phút"
    else:
        water_amount = "0 lít"
        duration = "Không cần tưới"

    # ===== AI WARNING =====
    ai_warning = None

    if soil_moisture < 0.15 and temperature > 32:
        ai_warning = "⚠️ Nguy cơ khô hạn cao, cần tưới gấp!"
    elif soil_moisture > 0.5:
        ai_warning = "⚠️ Nguy cơ úng nước, không nên tưới!"
    elif temperature > 35:
        ai_warning = "⚠️ Nhiệt độ quá cao, cây dễ bị stress!"

        print("===== DỮ LIỆU MỚI =====")
        print("soil_moisture:", soil_moisture)
        print("rain:", rain)
        print("eto:", eto)
        print("temperature:", temperature)
        print("humidity:", humidity)
        print("radiation:", radiation)

        print("===== AI KẾT QUẢ =====")
        print("score:", score)
        print("irrigation_status:", irrigation_status)
        print("proba:", proba)

    farms = get_latest_garden_data()

    top_dry_farms = sorted(farms, key=lambda x: x["soil"])[:5]
    wet_farms = [f for f in farms if f["soil"] > 0.48]
    high_priority_count = sum(1 for f in farms if "nhiều" in f["status"].lower())
    safe_count = sum(1 for f in farms if "không tưới" in f["status"].lower() or "ít" in f["status"].lower())

    farm_ai_summary = (
        f"AI đang theo dõi {len(farms)} vườn. "
        f"Hiện có {high_priority_count} vườn cần ưu tiên tưới "
        f"và {len(wet_farms)} vườn có nguy cơ úng."
    )
    context = {
        "temperature": temperature,
        "humidity": humidity,
        "rain": rain,
        "wind": wind,
        "radiation": radiation,
        "soil_moisture": soil_moisture,
        "eto": eto,
        "ai_score": score,
        "irrigation_status": irrigation_status,
        "ai_proba": proba,
        "ai_explanation": ai_explanation_text,
        "water_amount": water_amount,
        "duration": duration,
        "ai_warning": ai_warning,
        "farms": farms,
        "top_dry_farms": top_dry_farms,
        "wet_farms": wet_farms,
        "farm_ai_summary": farm_ai_summary,
        "high_priority_count": high_priority_count,
        "safe_count": safe_count,
        "labels": ['10h','11h','12h','13h','14h'],
        "values": [30,31,32,31,30],
        "soil_labels": ['10h','11h','12h','13h','14h'],
        "soil_values": [0.2,0.25,0.3,0.28,0.27],
        "current_time": datetime.now().strftime("%H:%M:%S"),
        "current_date": datetime.now().strftime("%d/%m/%Y"),
    }
    return render(request, "dashboard.html", context)

@csrf_exempt
def compare_gardens(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    try:
        data = json.loads(request.body)
        garden_ids = data.get("garden_ids", [])

        if not garden_ids:
            return JsonResponse({"error": "Chưa chọn vườn nào"}, status=400)

        result = []
        priority_farm = None
        highest_risk = -1

        for gid in garden_ids:
            garden = Garden.objects.filter(id=gid).first()
            realtime = GardenRealtime.objects.filter(garden=garden).order_by('-time').first()

            if garden and realtime:
                farm_data = {
                    "id": garden.id,
                    "name": garden.name,
                    "soil": realtime.soil_moisture,
                    "rain": realtime.rain,
                    "eto": realtime.et0,
                    "temp": realtime.temperature,
                    "humidity": realtime.humidity,
                    "radiation": realtime.radiation,
                    "ai_score": realtime.ai_score,
                    "ai_status": realtime.ai_status,
                }

                result.append(farm_data)

                risk = (1 - realtime.soil_moisture) + realtime.et0 + (realtime.temperature / 100)
                if risk > highest_risk:
                    highest_risk = risk
                    priority_farm = farm_data

        ai_summary = ""
        if priority_farm:
            ai_summary = (
                f"🤖 AI nhận định: {priority_farm['name']} cần ưu tiên hơn vì "
                f"độ ẩm đất thấp hơn và điều kiện bốc thoát hơi nước cao hơn."
            )

        return JsonResponse({
            "comparison": result,
            "ai_summary": ai_summary
        })

    except Exception as e:
        print("❌ compare_gardens lỗi:", e)
        return JsonResponse({"error": "Lỗi khi so sánh vườn"}, status=500)

def ahp_ai_data(request):
    farms = get_latest_garden_data()

    if not farms:
        return JsonResponse({"error": "Không có dữ liệu vườn"}, status=404)

    ranked = sorted(farms, key=lambda x: x["soil"])[:5]

    ai_cards = []

    for farm in ranked:
        ai_cards.append({
            "id": farm["id"],
            "name": farm["name"],
            "soil": farm["soil"],
            "status": farm["status"],
            "score": farm["score"],
            "explanation": get_farm_ai_explanation(farm)
        })

    return JsonResponse({
        "top_priority": ai_cards,
        "summary": "🤖 AI đang ưu tiên các vườn có độ ẩm thấp, ET₀ cao và nhiệt độ cao."
    })
# =====================
# Realtime weather API
# =====================
def realtime_data(request):
    cache_session = requests_cache.CachedSession('.cache', expire_after=15)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 12.3977,
        "longitude": 108.2181,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "rain",
            "wind_speed_10m",
            "shortwave_radiation"
        ]
    }

    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]
    current = response.Current()

    data = {
        "temperature": round(current.Variables(0).Value(), 2),
        "humidity": round(current.Variables(1).Value(), 2),
        "rain": round(current.Variables(2).Value(), 2),
        "wind": round(current.Variables(3).Value(), 2),
        "radiation": round(current.Variables(4).Value(), 2),
    }

    return JsonResponse(data)

# =====================
# AHP irrigation tool
# =====================
@csrf_exempt
def calculate_irrigation(request):
    if request.method == "POST":
        soil = float(request.POST.get("soil", 0))
        rain = float(request.POST.get("rain", 0))
        eto = float(request.POST.get("eto", 0))
        temp = float(request.POST.get("temp", 0))
        humidity = float(request.POST.get("humidity", 0))
        radiation = float(request.POST.get("radiation", 0))

        score = (
            soil * 0.28 +
            rain * 0.11 +
            eto * 0.25 +
            temp * 0.13 +
            humidity * 0.07 +
            radiation * 0.15
        )

        if score < 20:
            result = "💧 Tưới nhiều"
            advice = "Độ ẩm đất thấp, cần tưới nhiều nước để duy trì cây trồng"
        elif score < 40:
            result = "💧 Tưới vừa"
            advice = "Độ ẩm đất ở mức trung bình, tưới vừa phải"
        elif score < 60:
            result = "💧 Tưới ít"
            advice = "Độ ẩm đất khá cao, chỉ cần tưới ít"
        else:
            result = "❌ Không tưới"
            advice = "Độ ẩm đất tốt, không cần tưới"

        return JsonResponse({
            "score": round(score, 2),
            "result": result,
            "advice": advice
        })

    return JsonResponse({"error": "Invalid request"})

# =====================
# MAP
# =====================
def map_view(request):
    return render(request, "map.html")

def map_status(request):
    farms = get_latest_garden_data()

    result = []

    for farm in farms:
        soil = farm["soil"]

        if soil < 0.2:
            color = "red"
            icon = "💧💧💧"
        elif soil < 0.3:
            color = "orange"
            icon = "💧💧"
        elif soil < 0.4:
            color = "yellow"
            icon = "💧"
        else:
            color = "green"
            icon = "✅"

        farm["color"] = color
        farm["icon"] = icon
        result.append(farm)

    return JsonResponse(result, safe=False)
# =====================
# SENSOR PAGE
# =====================
def sensor_page(request):
    return render(request, "sensor.html")

def get_current_weather():
    """Lấy dữ liệu thời tiết hiện tại, trả về dict hoặc None nếu lỗi"""
    try:
        cache_session = requests_cache.CachedSession('.cache', expire_after=15)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        openmeteo = openmeteo_requests.Client(session=retry_session)
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 12.3977,
            "longitude": 108.2181,
            "current": ["temperature_2m", "relative_humidity_2m", "rain", "wind_speed_10m", "shortwave_radiation"]
        }
        responses = openmeteo.weather_api(url, params=params)
        current = responses[0].Current()
        return {
            "temperature": round(current.Variables(0).Value(), 2),
            "humidity": round(current.Variables(1).Value(), 2),
            "rain": round(current.Variables(2).Value(), 2),
            "wind": round(current.Variables(3).Value(), 2),
            "radiation": round(current.Variables(4).Value(), 2),
        }
    except Exception as e:
        print("Lỗi lấy thời tiết:", e)
        return None

# =====================
# CHATBOT AI
# =====================
@csrf_exempt
def chatbot_response(request):
    if request.method != "POST":
        return JsonResponse({"reply": "Yêu cầu không hợp lệ"})

    try:
        data = json.loads(request.body)
        user_message = data.get("message", "").strip()
        if not user_message:
            return JsonResponse({"reply": "Bạn chưa nhập tin nhắn."})

        # --- Kiểm tra và sửa session ---
        if 'chat_history' not in request.session or not isinstance(request.session['chat_history'], list):
            request.session['chat_history'] = []
        chat_history = request.session['chat_history']

        # --- Lấy dữ liệu thực tế ---
        farms = get_detailed_farm_data()
        if not isinstance(farms, list):
            farms = []

        weather = get_current_weather()
        if not isinstance(weather, dict):
            weather = {"temperature": 28, "humidity": 65, "rain": 0, "wind": 3, "radiation": 220}

        forecast = get_weather_forecast()
        if not isinstance(forecast, list):
            forecast = []

        # --- Xây dựng farm_summary an toàn ---
        farm_summary_lines = []
        for f in farms[:10]:
            if not isinstance(f, dict):
                continue
            name = f.get('name', '?')
            soil = f.get('soil', 0)
            soil_trend = f.get('soil_trend', [])
            if not isinstance(soil_trend, list):
                soil_trend = []
            trend_str = ', '.join(str(v) for v in soil_trend[:3]) if soil_trend else 'chưa có'
            temp = f.get('temp', '?')
            rain = f.get('rain', '?')
            eto = f.get('eto', '?')
            status = f.get('status', '?')
            farm_summary_lines.append(
                f"- Vườn {name}: độ ẩm {soil:.2f} (xu hướng {trend_str}), "
                f"nhiệt độ {temp}°C, mưa {rain} mm, ETo {eto}, AI: {status}"
            )
        farm_summary = "\n".join(farm_summary_lines) if farm_summary_lines else "Chưa có dữ liệu vườn."

        # --- Dự báo thời tiết ---
        forecast_lines = []
        for f in forecast[:3]:
            if not isinstance(f, dict):
                continue
            date = f.get('date', '?')
            temp_max = f.get('temp_max', '?')
            temp_min = f.get('temp_min', '?')
            rain = f.get('rain', '?')
            forecast_lines.append(f"- Ngày {date}: max {temp_max}°C / min {temp_min}°C, mưa {rain} mm")
        forecast_summary = "\n".join(forecast_lines) if forecast_lines else "Không có dữ liệu dự báo."

        # --- Context cho Gemini ---
        system_context = f"""Bạn là trợ lý AI chuyên về tưới tiêu thông minh cho vườn cà phê.
        Hãy trả lời câu hỏi bằng tiếng Việt, ngắn gọn, dễ hiểu, dùng biểu tượng cảm xúc nếu phù hợp.

        === DỮ LIỆU THỜI TIẾT HIỆN TẠI ===
        Nhiệt độ: {weather.get('temperature', '?')}°C
        Độ ẩm KK: {weather.get('humidity', '?')}%
        Lượng mưa: {weather.get('rain', '?')} mm
        Gió: {weather.get('wind', '?')} km/h
        Bức xạ: {weather.get('radiation', '?')} W/m²

        === DỰ BÁO 3 NGÀY TỚI ===
        {forecast_summary}

        === DỮ LIỆU CÁC VƯỜN ===
        {farm_summary}

        Câu hỏi của người dùng: "{user_message}"
        """

        # --- Tạo conversation ---
        prompt_parts = [system_context]
        for msg in chat_history[-5:]:
            if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                prefix = "Người dùng: " if msg['role'] == 'user' else "Trợ lý: "
                prompt_parts.append(prefix + msg['content'])
        prompt_parts.append("Người dùng: " + user_message)
        full_prompt = "\n\n".join(prompt_parts)

        # --- Gọi Gemini với prompt dạng text ---
        try:
            response = gemini_client.models.generate_content(
                model="models/gemini-2.0-flash",
                contents=full_prompt   # truyền string, không phải list dict
            )
            bot_reply = response.text.strip()
        except Exception as e:
            print("Gemini lỗi, fallback:", e)
            bot_reply = simple_rule_based_fallback(user_message, farms, request)

        # --- Lưu lịch sử (đảm bảo session là list) ---
        if not isinstance(request.session.get('chat_history'), list):
            request.session['chat_history'] = []
        request.session['chat_history'].append({"role": "user", "content": user_message})
        request.session['chat_history'].append({"role": "model", "content": bot_reply})
        if len(request.session['chat_history']) > 20:
            request.session['chat_history'] = request.session['chat_history'][-20:]
        request.session.modified = True

        return JsonResponse({"reply": bot_reply})

    except Exception as e:
        print("Lỗi chatbot_response:", e)
        import traceback
        traceback.print_exc()
        return JsonResponse({"reply": f"⚠️ Lỗi hệ thống: {str(e)}"})
    
def simple_rule_based_fallback(message, farms, request=None):
    if not isinstance(farms, list):
        farms = []
    msg_lower = message.lower()

    # ==================== HỎI DANH SÁCH VƯỜN TỪ CÂU TRƯỚC ====================
    if any(k in msg_lower for k in ["tên những vườn", "những vườn nào", "tên các vườn", "danh sách vườn", "vườn đó là gì", "tên các vườn đó"]):
        if request:
            last_list = request.session.get('last_farm_list', [])
            if last_list:
                # Giới hạn hiển thị tối đa 20 tên để tránh quá dài
                if len(last_list) <= 20:
                    return f"📋 Danh sách {len(last_list)} vườn cần tưới nhiều:\n" + ", ".join(last_list)
                else:
                    # Hiển thị 20 tên đầu và thông báo còn lại
                    display = ", ".join(last_list[:20])
                    return f"📋 Danh sách {len(last_list)} vườn cần tưới nhiều (hiển thị 20):\n{display}\n... và {len(last_list)-20} vườn khác."
            else:
                return "Chưa có dữ liệu về danh sách vườn. Hãy hỏi 'Bao nhiêu vườn cần tưới nhiều?' trước."
        return "Chưa có dữ liệu."

    # ==================== DỰ BÁO THỜI TIẾT ====================
    if any(k in msg_lower for k in ["ngày mai", "dự báo", "mai có mưa", "mai mưa"]):
        forecast = get_weather_forecast()
        if forecast and len(forecast) >= 2:  # forecast[0] hôm nay, [1] ngày mai
            tomorrow = forecast[1]
            rain = tomorrow.get('rain', 0)
            temp_max = tomorrow.get('temp_max', '?')
            if rain > 0:
                return f"☁️ Dự báo ngày mai: có mưa, lượng mưa {rain} mm, nhiệt độ cao nhất {temp_max}°C."
            else:
                return f"☀️ Dự báo ngày mai: không mưa, nhiệt độ cao nhất {temp_max}°C."
        return "Hiện chưa có dữ liệu dự báo thời tiết."

    # ==================== CẢNH BÁO HẠN HÁN ====================
    if "hạn hán" in msg_lower or "cảnh báo hạn" in msg_lower:
        if farms:
            dry_farms = [f for f in farms if f.get("soil", 1) < 0.2]
            if dry_farms:
                names = ", ".join([f.get("name", "?") for f in dry_farms[:3]])
                return f"⚠️ Cảnh báo: {len(dry_farms)} vườn có độ ẩm thấp (dưới 0.2), cần tưới: {names}."
            else:
                return "✅ Hiện chưa có dấu hiệu hạn hán, độ ẩm đất ổn định."
        return "Chưa có dữ liệu vườn để đánh giá."

    # ==================== THỜI TIẾT HIỆN TẠI ====================
    if any(k in msg_lower for k in ["thời tiết", "nhiệt độ", "độ ẩm", "mưa", "gió", "bức xạ"]):
        weather = get_current_weather()
        if weather:
            return (f"🌤 Thời tiết hiện tại: {weather['temperature']}°C, độ ẩm {weather['humidity']}%, "
                    f"mưa {weather['rain']} mm, gió {weather['wind']} km/h, bức xạ {weather['radiation']} W/m².")
        return "Không lấy được dữ liệu thời tiết."

    # ==================== KHUYẾN NGHỊ TƯỚI ====================
    if any(k in msg_lower for k in ["có nên tưới", "tưới nước", "nên tưới"]):
        if farms:
            avg_soil = sum(f.get("soil", 0) for f in farms) / len(farms)
            if avg_soil < 0.25:
                return "🌱 Độ ẩm đất trung bình thấp, bạn nên tưới nước hôm nay."
            elif avg_soil > 0.45:
                return "💧 Độ ẩm đất đang cao, không cần tưới hôm nay."
            else:
                return "🌿 Độ ẩm đất ở mức ổn định, có thể tưới nhẹ nếu cần."
        return "Chưa có dữ liệu độ ẩm đất."

    # ==================== SỐ LƯỢNG VƯỜN TƯỚI NHIỀU ====================
    if any(k in msg_lower for k in ["bao nhiêu vườn", "có mấy vườn", "số lượng vườn"]) and ("tưới nhiều" in msg_lower or "cần tưới" in msg_lower):
        high_farms = [f for f in farms if "nhiều" in f.get("status", "").lower()]
        count = len(high_farms)
        farm_names = [f.get("name", "?") for f in high_farms]
        # Lưu danh sách vào session
        if request:
            request.session['last_farm_list'] = farm_names
            request.session.modified = True
        if count == 0:
            return "💧 Hiện không có vườn nào cần tưới nhiều."
        return f"⚠️ Hiện có {count} vườn cần tưới nhiều."

    # ==================== CÁC CÂU HỎI KHÁC ====================
    if "khô nhất" in msg_lower:
        if farms:
            driest = min(farms, key=lambda x: x.get("soil", 1))
            return f"🌱 Vườn khô nhất: {driest.get('name', '?')} (độ ẩm {driest.get('soil', 0):.2f})"
        return "Chưa có dữ liệu vườn."

    if "úng" in msg_lower or "quá ẩm" in msg_lower:
        wet = [f.get("name", "?") for f in farms if f.get("soil", 0) > 0.48]
        if wet:
            return "⚠️ Vườn có nguy cơ úng: " + ", ".join(wet)
        return "✅ Không có vườn nào bị úng."

    return "🤖 Tôi chưa hiểu câu hỏi. Bạn có thể hỏi về thời tiết, dự báo, tình trạng vườn hoặc khuyến nghị tưới."

def get_detailed_farm_data():
    farms = get_latest_garden_data()
    result = []
    for f in farms:
        garden = Garden.objects.filter(id=f["id"]).first()
        if garden:
            history = GardenRealtime.objects.filter(garden=garden).order_by('-time')[:6]
            soil_trend = [round(h.soil_moisture, 3) for h in history] if history else []
        else:
            soil_trend = []
        result.append({
            "id": f["id"],
            "name": f["name"],
            "soil": f["soil"],
            "soil_trend": soil_trend,   # luôn là list
            "temp": f["temp"],
            "rain": f["rain"],
            "eto": f["eto"],
            "status": f["status"]
        })
    return result

def get_weather_forecast():
    try:
        cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
        retry_session = retry(cache_session, retries=3)
        openmeteo = openmeteo_requests.Client(session=retry_session)
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 12.3977,
            "longitude": 108.2181,
            "daily": ["temperature_2m_max", "temperature_2m_min", "rain_sum"],
            "timezone": "Asia/Bangkok"
        }
        responses = openmeteo.weather_api(url, params=params)
        daily = responses[0].Daily()
        times = daily.Time()
        if not hasattr(times, '__len__'):
            return []
        temps_max = daily.Variables(0).ValuesAsNumpy()
        temps_min = daily.Variables(1).ValuesAsNumpy()
        rains = daily.Variables(2).ValuesAsNumpy()
        
        forecast = []
        for i in range(min(3, len(times))):
            forecast.append({
                "date": times[i].strftime("%d/%m"),
                "temp_max": round(temps_max[i], 1),
                "temp_min": round(temps_min[i], 1),
                "rain": round(rains[i], 1)
            })
        return forecast
    except Exception as e:
        print("Lỗi forecast:", e)
        return []
# =====================
# OTHER PAGES
# =====================
def irrigation_page(request):
    return render(request, "irrigation_control.html")

def about_page(request):
    return render(request, "about.html")

def ahp_page(request):
    return render(request, "ahp.html")

def get_weather(request):
    data = WeatherData.objects.all().order_by('-time')[:50]
    result = []
    for d in data:
        result.append({
            "time": d.time.strftime("%Y-%m-%d %H:%M:%S"),
            "temperature": d.temperature,
            "humidity": d.humidity,
            "rain": d.rain,
            "radiation": d.radiation
        })
    return JsonResponse(result, safe=False)

def ahp_view(request):
    weights = AHPWeights.objects.all().order_by('criterion')
    scores = AlternativeScore.objects.all()
    
    alternatives = ['PA1', 'PA2', 'PA3', 'PA4']
    total_scores = {}
    
    for alt in alternatives:
        total = 0
        for w in weights:
            score = scores.get(alternative=alt, criterion=w.criterion).score
            total += w.weight * score
        total_scores[alt] = round(total * 100, 2)
    
    ranked = sorted(total_scores.items(), key=lambda x: x[1], reverse=True)
    
    context = {
        'weights': weights,
        'scores': scores,
        'total_scores': total_scores,
        'ranked': ranked,
    }
    
    return render(request, 'ahp.html', context)



def sensor_data(request):
    data = {
        "temperature": 30,
        "humidity": 70,
        "soil_moisture": 55
    }
    return JsonResponse(data)