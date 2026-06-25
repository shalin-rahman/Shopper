import 'package:shopper_mobile/domain/entities/product.dart';

class DemoData {
  static final sampleProduct1 = Product(
    id: 'p1',
    nameEn: 'Sample Laptop',
    price: 999.99,
    stockQuantity: 10,
    isActive: true,
    isTaxable: true,
    category: 'Electronics',
    brand: 'TechCorp',
    barcode: '1234567890',
    createdAt: DateTime.now(),
    updatedAt: DateTime.now(),
  );

  static final sampleProduct2 = Product(
    id: 'p2',
    nameEn: 'Sample Shirt',
    price: 29.99,
    stockQuantity: 50,
    isActive: true,
    isTaxable: true,
    category: 'Clothing',
    brand: 'FashionCo',
    barcode: '0987654321',
    createdAt: DateTime.now(),
    updatedAt: DateTime.now(),
  );

  static final List<Product> sampleProducts = [sampleProduct1, sampleProduct2];
}
