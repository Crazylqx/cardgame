from django.db import models

# Create your models here.
class User(models.Model):
    name = models.CharField(max_length = 32, unique = True)
    true_name = models.CharField(max_length = 32)
    password = models.CharField(max_length = 80)
    email = models.EmailField(unique = True)
    gender = models.BooleanField()  # male == True
    registerTime = models.DateTimeField(auto_now_add = True)
    confirmed = models.BooleanField(default=False)
    confirm_code = models.CharField(max_length = 80)
    def __str__(self):
        return self.name
