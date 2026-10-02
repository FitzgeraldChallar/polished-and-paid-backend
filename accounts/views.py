from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from rest_framework import serializers, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import CustomerProfile, Address, WishlistItem
User=get_user_model()
class UserSerializer(serializers.ModelSerializer):
    phone=serializers.SerializerMethodField()
    class Meta: model=User; fields=['id','username','email','first_name','last_name','phone']
    def get_phone(self,obj): return getattr(getattr(obj,'profile',None),'phone','')
class AddressSerializer(serializers.ModelSerializer):
    class Meta: model=Address; exclude=['user']
class RegisterSerializer(serializers.Serializer):
    email=serializers.EmailField(); password=serializers.CharField(min_length=8,write_only=True); first_name=serializers.CharField(required=False,allow_blank=True); last_name=serializers.CharField(required=False,allow_blank=True); phone=serializers.CharField(required=False,allow_blank=True)
    def create(self,data):
        email=data['email'].lower(); username=email
        if User.objects.filter(username=username).exists(): raise serializers.ValidationError({'email':'An account with this email already exists.'})
        with transaction.atomic():
            user=User.objects.create_user(username=username,email=email,password=data['password'],first_name=data.get('first_name',''),last_name=data.get('last_name',''))
            CustomerProfile.objects.create(user=user,phone=data.get('phone',''))
        return user
class RegisterView(APIView):
    permission_classes=[AllowAny]
    def post(self,request):
        s=RegisterSerializer(data=request.data); s.is_valid(raise_exception=True); user=s.save(); token=Token.objects.create(user=user); return Response({'token':token.key,'user':UserSerializer(user).data},status=201)
class LoginView(APIView):
    permission_classes=[AllowAny]
    def post(self,request):
        identifier=request.data.get('email') or request.data.get('username'); password=request.data.get('password'); user=authenticate(username=identifier.lower() if identifier else '',password=password)
        if not user: return Response({'detail':'Invalid email or password.'},status=400)
        token,_=Token.objects.get_or_create(user=user); return Response({'token':token.key,'user':UserSerializer(user).data})
class LogoutView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request): Token.objects.filter(user=request.user).delete(); return Response({'detail':'Logged out.'})
class ProfileView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request): return Response(UserSerializer(request.user).data)
    def patch(self,request):
        user=request.user
        for f in ['first_name','last_name']:
            if f in request.data: setattr(user,f,request.data[f])
        if 'email' in request.data:
            email=request.data['email'].lower(); user.email=email; user.username=email
        user.save(); phone=request.data.get('phone')
        if phone is not None: CustomerProfile.objects.update_or_create(user=user,defaults={'phone':phone})
        return Response(UserSerializer(user).data)
class AddressViewSet(viewsets.ModelViewSet):
    serializer_class=AddressSerializer; permission_classes=[IsAuthenticated]
    def get_queryset(self): return Address.objects.filter(user=self.request.user)
    def perform_create(self,serializer):
        if serializer.validated_data.get('is_default'): Address.objects.filter(user=self.request.user).update(is_default=False)
        serializer.save(user=self.request.user)
    def perform_update(self,serializer):
        if serializer.validated_data.get('is_default'): Address.objects.filter(user=self.request.user).update(is_default=False)
        serializer.save()


class WishlistItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)

    class Meta:
        model = WishlistItem
        fields = ['id', 'product_id', 'product_slug', 'created_at']
        read_only_fields = fields


class WishlistView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = WishlistItem.objects.filter(
            user=request.user
        ).select_related('product')
        return Response(WishlistItemSerializer(items, many=True).data)

    def post(self, request):
        product_id = request.data.get('product_id')
        if not product_id:
            return Response(
                {'detail': 'product_id is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            product_id = int(product_id)
        except (TypeError, ValueError):
            return Response(
                {'detail': 'product_id must be a valid integer.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from catalog.models import Product

        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response(
                {'detail': 'Product not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        item, created = WishlistItem.objects.get_or_create(
            user=request.user,
            product=product,
        )

        return Response(
            WishlistItemSerializer(item).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, product_id=None):
        if not product_id:
            return Response(
                {'detail': 'product_id is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted, _ = WishlistItem.objects.filter(
            user=request.user,
            product_id=product_id,
        ).delete()

        if not deleted:
            return Response(
                {'detail': 'Wishlist item not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)
