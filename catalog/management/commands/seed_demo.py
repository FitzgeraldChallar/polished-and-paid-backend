from django.core.management.base import BaseCommand
from catalog.models import Category, Product, ProductImage

DATA = {
    'Beauty & Skincare': [
        ('Radiance Glow Serum','BEA-001','A lightweight glow serum for an everyday radiant finish.',39.00,29.00,24,True,True,True,'https://images.unsplash.com/photo-1620916566398-39f1143ab7ba?auto=format&fit=crop&w=900&q=85'),
        ('Hydra Facial Cream','BEA-002','Daily moisturizing cream with a soft, luxurious finish.',34.00,None,30,True,True,False,'https://images.unsplash.com/photo-1556229010-6c3f2c9ca5f8?auto=format&fit=crop&w=900&q=85'),
    ],
    'Fragrance': [
        ('Velvet Bloom Eau de Parfum','FRA-001','A warm floral fragrance with a modern feminine character.',68.00,59.00,15,True,True,True,'https://images.unsplash.com/photo-1541643600914-78b084683601?auto=format&fit=crop&w=900&q=85'),
        ('Soft Amber Mist','FRA-002','A delicate everyday fragrance mist.',32.00,None,20,False,True,False,'https://images.unsplash.com/photo-1594035910387-fea47794261f?auto=format&fit=crop&w=900&q=85'),
    ],
    'Jewelry & Beads': [
        ('Gold Statement Hoops','JWL-001','Elegant hoops designed for everyday polish.',42.00,None,18,True,True,True,'https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?auto=format&fit=crop&w=900&q=85'),
    ],
    'Hair Products': [
        ('Silk Edge Control','HAI-001','Smooth-hold styling essential.',18.00,15.00,40,False,True,True,'https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=900&q=85'),
    ],
    'Self-Care': [
        ('Self-Care Ritual Set','SEL-001','A curated set for your everyday reset.',55.00,45.00,12,True,True,True,'https://images.unsplash.com/photo-1608571423902-eed4a5ad8108?auto=format&fit=crop&w=900&q=85'),
    ],
    'Health & Supplements': [
        ('Daily Wellness Essentials','WEL-001','A lifestyle wellness essential.',28.00,None,25,False,True,False,'https://images.unsplash.com/photo-1600185365483-26d7a4cc7519?auto=format&fit=crop&w=900&q=85'),
    ],
    'Household': [
        ('Home Care Essentials','HOU-001','Useful everyday home essentials.',24.00,None,35,False,False,False,'https://images.unsplash.com/photo-1583947215259-38e31be8751f?auto=format&fit=crop&w=900&q=85'),
    ],
    'Digital Products': [
        ('Polish & Pay Beauty Planner','DIG-001','A downloadable beauty and self-care planner.',12.00,None,999,True,True,True,'https://images.unsplash.com/photo-1517842645767-c639042777db?auto=format&fit=crop&w=900&q=85'),
    ],
}

class Command(BaseCommand):
    help='Create demo Polish & Pay categories and products.'
    def handle(self,*args,**kwargs):
        created=0
        for category_name, products in DATA.items():
            category,_=Category.objects.get_or_create(name=category_name,defaults={'is_active':True})
            for name,sku,desc,price,sale,stock,featured,new,bestseller,url in products:
                product,was_created=Product.objects.get_or_create(sku=sku,defaults={'category':category,'name':name,'description':desc,'short_description':desc,'price':price,'sale_price':sale,'stock_quantity':stock,'featured':featured,'is_new':new,'bestseller':bestseller,'is_active':True})
                if was_created:
                    ProductImage.objects.create(product=product,image_url=url,is_primary=True)
                    created += 1
        self.stdout.write(self.style.SUCCESS(f'Demo catalog ready. Created {created} products.'))
