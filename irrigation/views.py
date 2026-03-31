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


# =====================
# CHATBOT AI
# =====================
@csrf_exempt
def chatbot_response(request):
    if request.method != "POST":
        return JsonResponse({"reply": "Yêu cầu không hợp lệ"})

    try:
        data = json.loads(request.body)
        raw_message = data.get("message", "").strip()
        message = normalize_text(raw_message)
        session_key = request.session.session_key or "guest"

        if session_key not in CHAT_MEMORY:
            CHAT_MEMORY[session_key] = {"last_farm": None}

        farms = get_latest_garden_data()
        memory = CHAT_MEMORY[session_key]

        reply = "🤖 Tôi chưa hiểu rõ, bạn thử hỏi cụ thể hơn nhé."

        # =====================
        # 1. TÌM VƯỜN THEO TÊN / SỐ
        # =====================
        matched_farm = None

        for farm in farms:
            if farm["name"].lower() in message:
                matched_farm = farm
                memory["last_farm"] = farm["name"]
                break

        # hỏi kiểu "vườn 5"
        match_number = re.search(r"vườn\s*(\d+)|vuon\s*(\d+)", message)
        if not matched_farm and match_number:
            farm_id = int(match_number.group(1) or match_number.group(2))
            matched_farm = next((f for f in farms if f["id"] == farm_id), None)
            if matched_farm:
                memory["last_farm"] = matched_farm["name"]

        # nếu user hỏi "tại sao" thì nhớ lại vườn trước
        if not matched_farm and any(k in message for k in ["tại sao", "vì sao", "có nên tưới", "nguy hiểm", "ổn không"]):
            last_farm_name = memory.get("last_farm")
            if last_farm_name:
                matched_farm = next((f for f in farms if f["name"] == last_farm_name), None)

        # =====================
        # 2. TRẢ LỜI THEO TỪNG VƯỜN
        # =====================
        if matched_farm:
            reasons = []

            if matched_farm["soil"] < 0.2:
                reasons.append("độ ẩm đất thấp")
            if matched_farm["rain"] < 1:
                reasons.append("lượng mưa thấp")
            if matched_farm["temp"] > 30:
                reasons.append("nhiệt độ cao")
            if matched_farm["radiation"] > 900:
                reasons.append("bức xạ mạnh")
            if matched_farm["eto"] > 3:
                reasons.append("ETo cao")

            if any(k in message for k in ["tại sao", "vì sao", "giải thích"]):
                if reasons:
                    reply = (
                        f"🤖 AI giải thích cho {matched_farm['name']}:\n"
                        f"- " + "\n- ".join(reasons) + "\n"
                        f"=> Hệ thống đề xuất: {matched_farm['status']}."
                    )
                else:
                    reply = f"🤖 {matched_farm['name']} đang ở trạng thái khá ổn định. AI đề xuất: {matched_farm['status']}."
            else:
                reply = (
                    f"📍 {matched_farm['name']}\n"
                    f"🌱 Độ ẩm đất: {matched_farm['soil']}\n"
                    f"🌡 Nhiệt độ: {matched_farm['temp']}°C\n"
                    f"🌧 Mưa: {matched_farm['rain']} mm\n"
                    f"💧 ETo: {matched_farm['eto']}\n"
                    f"🤖 AI: {matched_farm['status']} (độ tin cậy {matched_farm['score']}/10)"
                )

            return JsonResponse({
                "reply": reply,
                "card": matched_farm
            })

        # =====================
        # 3. TOP KHÔ NHẤT / TƯỚI GẤP
        # =====================
        if has_any(message, [
            "khô nhất",
            "vườn nào khô",
            "vuon nao kho",
            "top",
            "top 1",
            "top 5",
            "cần tưới",
            "can tuoi",
            "tưới gấp",
            "tuoi gap",
            "ưu tiên",
            "uu tien",
            "nên tưới",
            "nen tuoi"
        ]):
            ranked = sorted(farms, key=lambda x: x["soil"])
            top5 = ranked[:5]
            names = ", ".join([f["name"] for f in top5])

            if "top 1" in message or "khô nhất" in message:
                top1 = top5[0]
                reply = f"🌱 Vườn khô nhất hiện tại là {top1['name']} (độ ẩm đất {top1['soil']})"
                return JsonResponse({"reply": reply, "card": top1})

            reply = f"🌱 Top 5 vườn cần ưu tiên tưới hiện tại là: {names}"
            return JsonResponse({"reply": reply, "top5": top5})

        # =====================
        # 4. ÚNG / QUÁ ẨM
        # =====================
        if has_any(message, ["úng", "quá ẩm", "ngập", "ẩm quá", "ướt quá", "ua nuoc"]):
            wet_farms = [f["name"] for f in farms if f["soil"] > 0.48]
            if wet_farms:
                reply = "⚠️ Các vườn có nguy cơ úng: " + ", ".join(wet_farms)
            else:
                reply = "✅ Hiện chưa có vườn nào có nguy cơ úng cao."
            return JsonResponse({"reply": reply})

        # =====================
        # 5. BAO NHIÊU VƯỜN TƯỚI NHIỀU
        # =====================
        if has_any(message, ["bao nhiêu", "có mấy", "thống kê", "bao nhieu"]) and has_any(message, ["tưới nhiều", "tuoi nhieu", "cần tưới", "can tuoi"]):
            count = sum(1 for f in farms if "nhiều" in f["status"].lower())
            reply = f"💧 Hiện có {count} vườn đang được AI đề xuất tưới nhiều."
            return JsonResponse({"reply": reply})

        # =====================
        # 6. AI DỰA VÀO GÌ
        # =====================
        if has_any(message, [
            "ai",
            "dựa vào gì",
            "dua vao gi",
            "ai dựa vào gì",
            "vì sao ai tưới",
            "sao ai biết",
            "ai hoạt động sao",
            "giai thich ai"
        ]):
            reply = "🤖 AI sử dụng độ ẩm đất, lượng mưa, ETo, nhiệt độ, độ ẩm không khí và bức xạ để đề xuất mức tưới phù hợp."
            return JsonResponse({"reply": reply})

        # =====================
        # 7. TƯ VẤN NÔNG NGHIỆP
        # =====================
        if "khi nào tưới" in message:
            reply = "🌤 Thời điểm tưới tốt nhất là sáng sớm hoặc chiều mát để giảm thất thoát nước."
            return JsonResponse({"reply": reply})

        if "độ ẩm đất bao nhiêu là tốt" in message:
            reply = "🌱 Với cà phê, độ ẩm đất ở mức trung bình ổn định thường phù hợp hơn là quá khô hoặc quá ướt."
            return JsonResponse({"reply": reply})

        # =====================
        # 8. CÂU HỎI TỰ NHIÊN / GẦN ĐÚNG
        # =====================
        if has_any(message, ["khô", "thiếu nước", "han", "khát nước"]):
            ranked = sorted(farms, key=lambda x: x["soil"])
            top1 = ranked[0]
            reply = f"🌱 Vườn có nguy cơ khô nhất hiện tại là {top1['name']} với độ ẩm đất {top1['soil']}."
            return JsonResponse({"reply": reply, "card": top1})

        if has_any(message, ["ổn không", "on khong", "có ổn không", "co on khong"]):
            dry_count = sum(1 for f in farms if f["soil"] < 0.2)
            wet_count = sum(1 for f in farms if f["soil"] > 0.48)
            reply = f"📋 Hiện hệ thống ghi nhận {dry_count} vườn có nguy cơ khô và {wet_count} vườn có nguy cơ úng."
            return JsonResponse({"reply": reply})

        if has_any(message, ["nên tưới lúc nào", "khi nào tưới", "luc nao tuoi", "thoi diem tuoi"]):
            reply = "🌤 Thời điểm tưới tốt nhất là sáng sớm hoặc chiều mát để giảm thất thoát nước."
            return JsonResponse({"reply": reply})

        if has_any(message, ["độ ẩm đất bao nhiêu là tốt", "do am dat tot", "độ ẩm tốt", "do am tot"]):
            reply = "🌱 Với cà phê, độ ẩm đất ở mức trung bình ổn định sẽ tốt hơn là quá khô hoặc quá ướt."
            return JsonResponse({"reply": reply})
        
        # =====================
        # 9. SO SÁNH 2 VƯỜN
        # =====================
        compare_match = re.findall(r"vườn\s*(\d+)|vuon\s*(\d+)", message)

        if ("so sánh" in message or "so sanh" in message) and len(compare_match) >= 2:
            ids = []
            for pair in compare_match:
                ids.append(int(pair[0] or pair[1]))

            selected = [f for f in farms if f["id"] in ids[:2]]

            if len(selected) == 2:
                f1, f2 = selected[0], selected[1]

                risk1 = (1 - f1["soil"]) + f1["eto"] + (f1["temp"] / 100)
                risk2 = (1 - f2["soil"]) + f2["eto"] + (f2["temp"] / 100)

                priority = f1 if risk1 > risk2 else f2

                reply = (
                    f"📊 So sánh {f1['name']} và {f2['name']}:\n"
                    f"- {f1['name']}: đất {f1['soil']}, ET₀ {f1['eto']}, nhiệt {f1['temp']}°C\n"
                    f"- {f2['name']}: đất {f2['soil']}, ET₀ {f2['eto']}, nhiệt {f2['temp']}°C\n\n"
                    f"🤖 AI đánh giá: {priority['name']} cần ưu tiên hơn."
                )

                return JsonResponse({"reply": reply})
        return JsonResponse({"reply": reply})
    except Exception as e:
        print("❌ chatbot_response lỗi:", e)
        return JsonResponse({"reply": "⚠️ Chatbot đang gặp lỗi xử lý dữ liệu."})
        

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