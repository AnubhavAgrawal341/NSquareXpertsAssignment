from django.db import models

class UploadedPDF(models.Model):
    file = models.FileField(upload_to='pdfs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    summary = models.TextField(blank=True, null=True)  # Bonus: Store auto-generated summary

    def __str__(self):
        return self.file.name

class ChatMessage(models.Model):
    pdf = models.ForeignKey(UploadedPDF, on_delete=models.CASCADE, related_name='messages')
    query = models.TextField()  # User's question
    answer = models.TextField()  # LLM's response
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Query on {self.pdf}: {self.query[:50]}..."

# Bonus: For entity extraction
class ExtractedEntity(models.Model):
    pdf = models.ForeignKey(UploadedPDF, on_delete=models.CASCADE, related_name='entities')
    entity_type = models.CharField(max_length=100)  # e.g., 'person', 'date', 'organization'
    entity_text = models.TextField()
    count = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.entity_type}: {self.entity_text}"