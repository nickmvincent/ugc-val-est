from django.db import models

class Post(models.Model):
    """A post"""
    body = models.CharField(max_length=10000)
    score = models.IntegerField()

    def __str__(self):
        return self.body
