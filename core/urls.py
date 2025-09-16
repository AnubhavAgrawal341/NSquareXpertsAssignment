from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_pdfs, name='home'),  # Add this: Root URL as homepage, showing PDF list
    path('upload/', views.upload_pdf, name='upload_pdf'),
    path('query/<int:pdf_id>/', views.query_pdf, name='query_pdf'),
    # Additional creative feature routes:
    # For auto-summarization (bonus): Generate summary after upload
    path('summary/<int:pdf_id>/', views.get_summary, name='get_summary'),
    # For entity extraction (bonus): Extract key entities from PDF
    path('entities/<int:pdf_id>/', views.extract_entities, name='extract_entities'),
    # For listing uploaded PDFs (multi-PDF support, bonus)
    path('list/', views.list_pdfs, name='list_pdfs'),
]