from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import SessionSkating, Payment, User
from .serializers import (
    SessionSkatingSerializer, 
    PaymentSerializer, 
    UserSerializer
)

class SessionSkatingViewSet(viewsets.ModelViewSet):
    queryset = SessionSkating.objects.all()
    serializer_class = SessionSkatingSerializer
    
    def get_queryset(self):
        queryset = SessionSkating.objects.all()
        
        # Filter by date if provided
        date = self.request.query_params.get('date', None)
        if date:
            queryset = queryset.filter(date=date)
        
        # Filter by payment status
        status = self.request.query_params.get('status', None)
        if status:
            queryset = queryset.filter(payment__status=status)
        
        return queryset.select_related('payment', 'payment__user')
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check if payment exists and is completed
        payment_id = request.data.get('payment')
        try:
            payment = Payment.objects.get(id=payment_id)
            if payment.status != 'COMPLETED':
                return Response(
                    {'error': 'Payment must be completed to create session'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, 
            status=status.HTTP_201_CREATED, 
            headers=headers
        )
    
    @action(detail=False, methods=['get'])
    def upcoming_sessions(self, request):
        """Get upcoming sessions"""
        from django.utils import timezone
        sessions = SessionSkating.objects.filter(
            start_time__gte=timezone.now()
        ).order_by('start_time')
        
        page = self.paginate_queryset(sessions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(sessions, many=True)
        return Response(serializer.data)

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    
    def get_queryset(self):
        queryset = Payment.objects.all()
        
        # Filter by user if provided
        user_id = self.request.query_params.get('user_id', None)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter by status if provided
        status = self.request.query_params.get('status', None)
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.select_related('user')
    
    @action(detail=True, methods=['post'])
    def complete_payment(self, request, pk=None):
        """Mark payment as completed"""
        payment = self.get_object()
        payment.status = 'COMPLETED'
        payment.save()
        
        serializer = self.get_serializer(payment)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def refund_payment(self, request, pk=None):
        """Mark payment as refunded"""
        payment = self.get_object()
        payment.status = 'REFUNDED'
        payment.save()
        
        serializer = self.get_serializer(payment)
        return Response(serializer.data)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    def get_queryset(self):
        queryset = User.objects.all()
        
        # Filter by role if provided
        role = self.request.query_params.get('role', None)
        if role:
            queryset = queryset.filter(role=role)
        
        return queryset
