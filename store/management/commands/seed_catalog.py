from django.core.management.base import BaseCommand

from store.models import Product, ProductVariant


CATALOG = [
    ('nova-x-5g', 'Nova X 5G', 'Smartphones', 'Nova', 899, 18,
     'Ultra-slim 6.7" OLED, AI camera suite, and premium wireless charging.',
     'https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=1200',
     ['120Hz OLED display', 'Triple-lens night camera', '65W fast charging', '5G connectivity']),
    ('aeroblade-14', 'AeroBlade 14', 'Laptops', 'Aero', 1499, 12,
     'Featherweight performance laptop with a premium aluminum chassis.',
     'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=1200',
     ['Intel i9 processor', '16GB RAM', '1TB SSD storage', 'Thunderbolt 4 support']),
    ('pulse-one', 'Pulse One Headphones', 'Audio', 'Pulse', 249, 30,
     'Noise-cancelling wireless headphones with studio-grade sound.',
     'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=1200',
     ['Active noise cancellation', '40-hour battery life', 'Hi-Res audio', 'Touch controls']),
    ('arc-gaming-pad', 'Arc Gaming Controller', 'Gaming', 'Arc', 129, 0,
     'Ergonomic wireless controller built for precision and comfort.',
     'https://images.unsplash.com/photo-1592840496694-26d035b52b48?w=1200',
     ['Low-latency Bluetooth', 'Custom macro buttons', 'RGB lighting', 'Haptic feedback']),
    ('home-sync-hub', 'Home Sync Hub', 'Smart Home', 'HomeSync', 179, 24,
     'All-in-one smart home controller with voice assistant compatibility.',
     'https://images.unsplash.com/photo-1558002038-1055907df827?w=1200',
     ['Voice control', 'Multi-device automation', 'Secure encryption', 'App monitoring']),
    ('galaxy-band', 'Galaxy Band S', 'Wearables', 'Galaxy', 159, 22,
     'Sleek fitness tracker with sleep analysis and health monitoring.',
     'https://images.unsplash.com/photo-1575311373937-040b8e1fd5b6?w=1200',
     ['24/7 heart rate monitoring', 'Sleep tracking', 'Water resistant', 'Smart notifications']),
    ('pixel-lite', 'Pixel Lite', 'Smartphones', 'Pixel', 699, 14,
     'Compact flagship with crisp display and powerful selfie camera.',
     'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=1200',
     ['6.1" OLED display', 'Dual camera', 'Wireless charging', 'Premium glass finish']),
    ('studio-book', 'StudioBook Pro', 'Laptops', 'Studio', 1999, 8,
     'High-performance creator laptop for editing, design, and animation.',
     'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=1200',
     ['2TB SSD option', 'NVIDIA RTX GPU', '4K display', 'Advanced cooling']),
    ('orbit-speaker', 'Orbit Smart Speaker', 'Smart Home', 'Orbit', 129, 31,
     'Premium compact speaker with immersive sound and voice controls.',
     'https://images.unsplash.com/photo-1589492477829-5e65395b66cc?w=1200',
     ['Premium bass', 'Multi-room support', 'AI assistant', 'Touch controls']),
    ('nova-watch', 'Nova Watch', 'Wearables', 'Nova', 229, 18,
     'Luxury smartwatch with customizable watch faces and health insights.',
     'https://images.unsplash.com/photo-1544117518-3befbc3b8a35?w=1200',
     ['GPS tracking', 'ECG monitoring', 'Long battery life', 'Premium strap options']),
    ('stealth-pro', 'Stealth Pro Laptop', 'Laptops', 'Stealth', 1799, 0,
     'Gaming laptop with fast refresh and high-end graphics for immersive play.',
     'https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=1200',
     ['RTX 4080', '240Hz display', 'RGB keyboard', 'Fast charging']),
    ('soundcore-max', 'Soundcore Max', 'Audio', 'Soundcore', 129, 36,
     'Portable wireless speaker with deep bass and glowing accents.',
     'https://images.unsplash.com/photo-1558403194-611308249627?w=1200',
     ['24-hour battery', 'Party lighting', 'Stereo pairing', 'IPX6 water resistance']),
    ('nova-vr', 'Nova VR', 'Gaming', 'Nova', 399, 11,
     'Immersive VR headset with crisp visuals and responsive motion tracking.',
     'https://images.unsplash.com/photo-1622979135225-d2ba269cf1ac?w=1200',
     ['120Hz panel', 'Spatial audio', 'Comfort fit', 'Inside-out tracking']),
    ('smart-sensor-kit', 'Smart Sensor Kit', 'Smart Home', 'SmartKit', 99, 48,
     'Fast-install smart sensors for doors, windows, and motion detection.',
     'https://images.unsplash.com/photo-1557002665-c552e1832483?w=1200',
     ['Quick setup', 'Battery powered', 'App alerts', 'Home automation']),
    ('zen-tab-pro', 'ZenTab Pro 12', 'Tablets', 'Zenith', 649, 16,
     'A premium tablet designed for illustration, work, and entertainment.',
     'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=1200',
     ['4K Video Support', 'Magnetic Stylus Charging', 'Quad-Speaker Array', 'Face Unlock']),
    ('vision-monitor-4k', 'Vision 32" 4K Monitor', 'Peripherals', 'Vision', 549, 13,
     'A color-accurate 4K productivity monitor for demanding creative work.',
     'https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=1200',
     ['99% DCI-P3 Color Space', 'Ultra-Thin Bezel', 'Height Adjustable Stand', 'HDR600 Certified']),
    ('titan-desktop', 'Titan Gaming Station', 'Desktops', 'Titan', 2499, 5,
     'An elite desktop workstation for gaming and heavyweight creative tasks.',
     'https://images.unsplash.com/photo-1587831990711-23ca6441447b?w=1200',
     ['Glass Side Panel', 'RGB Lighting', 'Silent Operation', 'VR Ready Elite']),
    ('aura-drone-4k', 'Aura 4K Drone', 'Gadgets', 'Aura', 799, 9,
     'A compact smart drone with stabilized 4K capture and subject tracking.',
     'https://images.unsplash.com/photo-1473968512447-ac175bb42fea?w=1200',
     ['Obstacle Avoidance', 'ActiveTrack 5.0', 'Level 5 Wind Resistance', 'RAW Photo Support']),
]

VARIANTS = {
    'nova-x-5g': [
        ('v1', '128GB', 15, 0), ('v2', '256GB', 3, 100),
        ('v3', '512GB', 0, 250),
    ],
    'titan-desktop': [
        ('v1', 'Standard Edition', 5, 0), ('v2', 'Titan Ultimate', 2, 800),
    ],
}


class Command(BaseCommand):
    help = 'Create or update the TechHub starter catalog.'

    def handle(self, *args, **options):
        for index, (
            slug, name, category, brand, price, stock, description, image, features
        ) in enumerate(CATALOG):
            product, _ = Product.objects.update_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'category': category,
                    'brand': brand,
                    'price': price,
                    'stock': stock,
                    'description': description,
                    'primary_image': image,
                    'images': [image],
                    'features': features,
                    'is_active': True,
                    'is_featured': index < 8,
                    'is_on_sale': index < 8,
                    'discount_percent': 20 if index < 8 else 0,
                },
            )
            for code, variant_name, variant_stock, modifier in VARIANTS.get(slug, []):
                ProductVariant.objects.update_or_create(
                    product=product, code=code,
                    defaults={
                        'name': variant_name,
                        'stock': variant_stock,
                        'price_modifier': modifier,
                    },
                )
        self.stdout.write(self.style.SUCCESS(
            f'Seeded {len(CATALOG)} products.'
        ))
