from django.shortcuts import render, redirect
from .models import CustomUser
from django.contrib import messages
from .models import Vehicle
from .models import Booking
from datetime import date
from django.db import models
from reportlab.pdfgen import canvas
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from .models import Feedback

def register(request):
    if request.method == 'POST':
        name = request.POST['name']
        email = request.POST['email']
        phone = request.POST['phone']
        password = request.POST['password']

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered')
            return redirect('register')

        CustomUser.objects.create(
            name=name,
            email=email,
            phone=phone,
            password=password
        )

        messages.success(request, 'Registration successful! Please login.')
        return redirect('login')

    return render(request, 'rental/register.html')

def login(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        user = CustomUser.objects.filter(email=email, password=password).first()

        if user:
            request.session['user_id'] = user.id
            request.session['user_name'] = user.name
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid email or password')
            return redirect('login')

    return render(request, 'rental/login.html')


def logout(request):
    request.session.flush()
    return redirect('login')

def dashboard(request):
    if 'user_id' not in request.session:
        return redirect('login')

    user = CustomUser.objects.get(id=request.session['user_id'])

    # get user's bookings
    bookings = Booking.objects.filter(user=user)

    recommended = []

    if bookings.exists():

        # most booked vehicle type
        vehicle_type = bookings.values_list(
            'vehicle__vehicle_type', flat=True
        )[0]

        recommended = Vehicle.objects.filter(vehicle_type=vehicle_type)[:3]

    context = {
        "recommended": recommended
    }

    return render(request, 'rental/dashboard.html', context)

def vehicle_list(request):
    if 'user_id' not in request.session:
        return redirect('login')

    query = request.GET.get('q')
    vehicle_type = request.GET.get('type')
    fuel_type = request.GET.get('fuel')
    location = request.GET.get('location')

    vehicles = Vehicle.objects.filter(is_available=True)

    if query:
        vehicles = vehicles.filter(name__icontains=query)

    if vehicle_type:
        vehicles = vehicles.filter(vehicle_type=vehicle_type)

    if fuel_type:
        vehicles = vehicles.filter(fuel_type__icontains=fuel_type)

    if location:
        vehicles = vehicles.filter(location__icontains=location)

    context = {
        "vehicles": vehicles
    }

    return render(request, 'rental/vehicle_list.html', context)

def book_vehicle(request, vehicle_id):
    if 'user_id' not in request.session:
        return redirect('login')

    vehicle = Vehicle.objects.get(id=vehicle_id)
    user = CustomUser.objects.get(id=request.session['user_id'])

    if request.method == 'POST':
        start_date = request.POST['start_date']
        end_date = request.POST['end_date']

        start_date = date.fromisoformat(start_date)
        end_date = date.fromisoformat(end_date)

        # check date validation
        if end_date < start_date:
            messages.error(request, "End date cannot be before start date.")
            return redirect('vehicle_list')

        # booking limit rule (max 3 active bookings)
        active_bookings = Booking.objects.filter(
            user=user,
            status__in=["Pending", "Confirmed"]
        ).count()

        if active_bookings >= 3:
            messages.error(request, "You can only have 3 active bookings at a time.")
            return redirect('vehicle_list')

        # check date conflict
        conflict = Booking.objects.filter(
            vehicle=vehicle,
            start_date__lte=end_date,
            end_date__gte=start_date,
            status__in=["Pending", "Confirmed"]
        ).exists()

        if conflict:
            messages.error(request, "Vehicle already booked for these dates.")
            return redirect('vehicle_list')

        days = (end_date - start_date).days + 1
        total_price = days * vehicle.price_per_day

        Booking.objects.create(
            user=user,
            vehicle=vehicle,
            start_date=start_date,
            end_date=end_date,
            total_price=total_price,
            status="Pending"
        )

        return redirect('my_bookings')

    booked_dates = Booking.objects.filter(
        vehicle=vehicle,
        status__in=["Pending", "Confirmed"]
    )

    return render(request, 'rental/book_vehicle.html', {
        'vehicle': vehicle,
        'booked_dates': booked_dates
    })

def my_bookings(request):
    if 'user_id' not in request.session:
        return redirect('login')

    bookings = Booking.objects.filter(user_id=request.session['user_id'])

    for booking in bookings:
        booking.days = (booking.end_date - booking.start_date).days + 1

    return render(request, 'rental/my_bookings.html', {'bookings': bookings})

def cancel_booking(request, booking_id):

    booking = get_object_or_404(Booking, id=booking_id)

    booking.status = "Cancelled"

    booking.save()

    return redirect('my_bookings')


def return_vehicle(request, booking_id):

    booking = get_object_or_404(Booking, id=booking_id)
    booking.status = "Returned"

    booking.save()

    return redirect('my_bookings')

def admin_dashboard(request):

    # basic statistics
    total_users = CustomUser.objects.count()
    total_vehicles = Vehicle.objects.count()
    total_bookings = Booking.objects.count()

    total_revenue = Booking.objects.filter(status="Returned").aggregate(
    total=models.Sum("total_price")
    )["total"] or 0

    # bookings by vehicle (for chart)
    vehicle_names = []
    booking_counts = []

    vehicles = Vehicle.objects.all()

    for v in vehicles:
        count = Booking.objects.filter(vehicle=v).count()
        vehicle_names.append(v.name)
        booking_counts.append(count)

    # vehicle popularity ranking
    popular_vehicles = []

    for v in vehicles:
        count = Booking.objects.filter(vehicle=v).count()
        popular_vehicles.append({
            "name": v.name,
            "count": count
        })

    popular_vehicles = sorted(popular_vehicles, key=lambda x: x["count"], reverse=True)

    # recent booking activity
    recent_bookings = Booking.objects.select_related(
        'user', 'vehicle'
    ).order_by('-id')[:5]

    context = {
        "total_users": total_users,
        "total_vehicles": total_vehicles,
        "total_bookings": total_bookings,
        "total_revenue": total_revenue,
        "vehicle_names": vehicle_names,
        "booking_counts": booking_counts,
        "popular_vehicles": popular_vehicles,
        "recent_bookings": recent_bookings
    }

    return render(request, "rental/admin_dashboard.html", context)

def download_receipt(request, booking_id):

    booking = Booking.objects.get(id=booking_id)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="receipt.pdf"'

    p = canvas.Canvas(response)

    p.drawString(100, 800, "Vehicle Rental Receipt")
    p.drawString(100, 760, f"User: {booking.user.name}")
    p.drawString(100, 740, f"Vehicle: {booking.vehicle.name}")
    p.drawString(100, 720, f"Start Date: {booking.start_date}")
    p.drawString(100, 700, f"End Date: {booking.end_date}")
    p.drawString(100, 680, f"Total Price: ₹{booking.total_price}")
    p.drawString(100, 660, f"Status: {booking.status}")

    p.showPage()
    p.save()

    return response

def add_vehicle(request):

    if 'user_id' not in request.session:
        return redirect('login')

    if request.method == "POST":

        name = request.POST['name']
        vehicle_type = request.POST['vehicle_type']
        fuel_type = request.POST['fuel_type']
        location = request.POST['location'].strip()
        price = request.POST['price']
        image = request.FILES.get('image')

        owner = CustomUser.objects.get(id=request.session['user_id'])

        vehicle_count = Vehicle.objects.filter(owner=owner).count()

        if vehicle_count >= 3:
            messages.error(request, "You can only add up to 3 vehicles.")
            return redirect('my_vehicles')

        Vehicle.objects.create(
            owner=owner,
            name=name,
            vehicle_type=vehicle_type,
            fuel_type=fuel_type,
            location=location,
            price_per_day=price,
            vehicle_image=image
        )

        return redirect('vehicle_list')

    return render(request, "rental/add_vehicle.html")

def my_vehicles(request):

    if 'user_id' not in request.session:
        return redirect('login')

    owner = CustomUser.objects.get(id=request.session['user_id'])

    vehicles = Vehicle.objects.filter(owner=owner)

    return render(request, "rental/my_vehicles.html", {"vehicles": vehicles})

def toggle_vehicle(request, vehicle_id):

    vehicle = Vehicle.objects.get(id=vehicle_id, owner_id=request.session['user_id'])

    if vehicle.is_available:
        vehicle.is_available = False
    else:
        vehicle.is_available = True

    vehicle.save()

    return redirect('my_vehicles')

def delete_vehicle(request, vehicle_id):
    if 'user_id' not in request.session:
        return redirect('login')

    vehicle = get_object_or_404(
    Vehicle,
    id=vehicle_id,
    owner_id=request.session['user_id']
    )
    vehicle.delete()

    return redirect('my_vehicles')

def edit_vehicle(request, vehicle_id):
    if 'user_id' not in request.session:
        return redirect('login')

    vehicle = get_object_or_404(
    Vehicle,
    id=vehicle_id,
    owner_id=request.session['user_id']
    )

    if request.method == "POST":

        vehicle.name = request.POST['name']
        vehicle.vehicle_type = request.POST['vehicle_type']
        vehicle.fuel_type = request.POST['fuel_type']
        vehicle.price_per_day = request.POST['price']

        vehicle.save()

        return redirect('my_vehicles')

    return render(request, "rental/edit_vehicle.html", {"vehicle": vehicle})

def owner_earnings(request):

    if 'user_id' not in request.session:
        return redirect('login')

    owner = CustomUser.objects.get(id=request.session['user_id'])

    vehicles = Vehicle.objects.filter(owner=owner)

    earnings_data = []
    total_earnings = 0

    for vehicle in vehicles:

        bookings = Booking.objects.filter(vehicle=vehicle, status="Returned")

        booking_count = bookings.count()

        revenue = bookings.aggregate(
            total=models.Sum("total_price")
        )["total"] or 0

        total_earnings += revenue

        earnings_data.append({
            "vehicle": vehicle.name,
            "bookings": booking_count,
            "revenue": revenue
        })

    context = {
        "earnings_data": earnings_data,
        "total_earnings": total_earnings
    }

    return render(request, "rental/owner_earnings.html", context)

def owner_bookings(request):

    if 'user_id' not in request.session:
        return redirect('login')

    owner = CustomUser.objects.get(id=request.session['user_id'])

    bookings = Booking.objects.filter(vehicle__owner=owner)

    return render(request, "rental/owner_bookings.html", {"bookings": bookings})

def approve_booking(request, booking_id):

    booking = Booking.objects.get(id=booking_id)

    booking.status = "Confirmed"
    booking.save()

    return redirect('owner_bookings')

def reject_booking(request, booking_id):

    booking = Booking.objects.get(id=booking_id)

    booking.status = "Rejected"
    booking.save()

    return redirect('owner_bookings')

def home(request):
    return render(request, "rental/home.html")

def add_feedback(request, vehicle_id):

    if 'user_id' not in request.session:
        return redirect('login')

    user = CustomUser.objects.get(id=request.session['user_id'])
    vehicle = Vehicle.objects.get(id=vehicle_id)

    if request.method == "POST":
        rating = request.POST['rating']
        comment = request.POST['comment']

        Feedback.objects.create(
            user=user,
            vehicle=vehicle,
            rating=rating,
            comment=comment
        )

        return redirect('vehicle_list')

    return render(request, "rental/add_feedback.html", {"vehicle": vehicle})