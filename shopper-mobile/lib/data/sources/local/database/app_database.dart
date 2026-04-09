import 'package:drift/drift.dart';
import 'package:drift_flutter/drift_flutter.dart';

part 'app_database.g.dart';

class Products extends Table {
  TextColumn get id => text()();
  TextColumn get name => text()();
  TextColumn get description => text().nullable()();
  TextColumn get barcode => text().nullable()();
  TextColumn get sku => text().nullable()();
  RealColumn get price => real()();
  RealColumn get costPrice => real().nullable()();
  RealColumn get sellPrice => real().nullable()();
  TextColumn get category => text().nullable()();
  TextColumn get brand => text().nullable()();
  TextColumn get imageUrl => text().nullable()();
  TextColumn get images => text().nullable()(); // JSON string of image URLs
  IntColumn get stockQuantity => integer()();
  IntColumn get minStockLevel => integer().nullable()();
  BoolColumn get isActive => boolean().withDefault(const Constant(true))();
  BoolColumn get isTaxable => boolean().withDefault(const Constant(false))();
  RealColumn get taxRate => real().nullable()();
  TextColumn get unit => text().nullable()();
  TextColumn get color => text().nullable()();
  TextColumn get size => text().nullable()();
  TextColumn get attributes => text().nullable()(); // JSON string of attributes
  TextColumn get specifications => text().nullable()(); // JSON string of specifications
  TextColumn get variants => text().nullable()(); // JSON string of variants
  DateTimeColumn get createdAt => dateTime()();
  DateTimeColumn get updatedAt => dateTime()();

  @override
  Set<Column> get primaryKey => {id};
}

class CartItems extends Table {
  TextColumn get id => text()();
  TextColumn get productId => text()();
  TextColumn get productName => text()();
  TextColumn get productImageUrl => text().nullable()();
  IntColumn get quantity => integer()();
  RealColumn get unitPrice => real()();
  RealColumn get discount => real().nullable()();
  TextColumn get notes => text().nullable()();
  DateTimeColumn get addedAt => dateTime()();

  @override
  Set<Column> get primaryKey => {id};
}

class Orders extends Table {
  TextColumn get id => text()();
  TextColumn get orderNumber => text()();
  RealColumn get subtotal => real()();
  RealColumn get discount => real().nullable()();
  RealColumn get taxAmount => real().nullable()();
  RealColumn get total => real()();
  TextColumn get status => text()();
  TextColumn get paymentStatus => text()();
  TextColumn get customerName => text().nullable()();
  TextColumn get customerPhone => text().nullable()();
  TextColumn get notes => text().nullable()();
  DateTimeColumn get createdAt => dateTime()();
  DateTimeColumn get updatedAt => dateTime()();

  @override
  Set<Column> get primaryKey => {id};
}

class OrderItems extends Table {
  TextColumn get id => text()();
  TextColumn get orderId => text().references(Orders, #id, onDelete: KeyAction.cascade)();
  TextColumn get productId => text()();
  TextColumn get productName => text()();
  IntColumn get quantity => integer()();
  RealColumn get unitPrice => real()();
  RealColumn get discount => real().nullable()();
  RealColumn get taxAmount => real().nullable()();
  TextColumn get notes => text().nullable()();

  @override
  Set<Column> get primaryKey => {id};
}

@DriftDatabase(tables: [Products, CartItems, Orders, OrderItems])
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(_openConnection());

  @override
  int get schemaVersion => 2;

  @override
  MigrationStrategy get migration => MigrationStrategy(
    onCreate: (m) async => await m.createAll(),
    onUpgrade: (m, from, to) async {
      if (from < 2) {
        // Add new columns for version 2
        await m.addColumn(products, products.sellPrice);
        await m.addColumn(products, products.images);
        await m.addColumn(products, products.color);
        await m.addColumn(products, products.size);
        await m.addColumn(products, products.attributes);
        await m.addColumn(products, products.specifications);
        await m.addColumn(products, products.variants);
      }
    },
  );

  static QueryExecutor _openConnection() {
    return driftDatabase(
      name: 'shopper_mobile_db',
      native: const DriftNativeOptions(
        databasePath: _databasePath,
      ),
    );
  }

  static String get _databasePath {
    return 'shopper_mobile.db';
  }

  // Product operations
  Future<List<Product>> getAllProducts() => select(products).get();

  Future<Product?> getProductById(String id) =>
      (select(products)..where((tbl) => tbl.id.equals(id))).getSingleOrNull();

  Future<void> insertProduct(ProductsCompanion product) =>
      into(products).insert(product, mode: InsertMode.insertOrReplace);

  Future<void> insertProducts(List<ProductsCompanion> productList) async {
    await batch((batch) {
      batch.insertAll(products, productList, mode: InsertMode.insertOrReplace);
    });
  }

  Future<void> updateProduct(ProductsCompanion product) =>
      update(products).replace(product);

  Future<void> deleteProduct(String id) =>
      (delete(products)..where((tbl) => tbl.id.equals(id))).go();

  Future<void> clearProducts() => delete(products).go();

  // Cart operations
  Future<List<CartItem>> getAllCartItems() => select(cartItems).get();

  Future<CartItem?> getCartItemById(String id) =>
      (select(cartItems)..where((tbl) => tbl.id.equals(id))).getSingleOrNull();

  Future<void> insertCartItem(CartItemsCompanion cartItem) =>
      into(cartItems).insert(cartItem, mode: InsertMode.insertOrReplace);

  Future<void> updateCartItem(CartItemsCompanion cartItem) =>
      update(cartItems).replace(cartItem);

  Future<void> deleteCartItem(String id) =>
      (delete(cartItems)..where((tbl) => tbl.id.equals(id))).go();

  Future<void> clearCart() => delete(cartItems).go();

  // Order operations
  Future<List<Order>> getAllOrders() => select(orders).get();

  Future<Order?> getOrderById(String id) =>
      (select(orders)..where((tbl) => tbl.id.equals(id))).getSingleOrNull();

  Future<void> insertOrder(OrdersCompanion order) =>
      into(orders).insert(order, mode: InsertMode.insertOrReplace);

  Future<void> updateOrder(OrdersCompanion order) =>
      update(orders).replace(order);

  Future<void> deleteOrder(String id) =>
      (delete(orders)..where((tbl) => tbl.id.equals(id))).go();

  Future<void> clearOrders() => delete(orders).go();

  // Order items operations
  Future<List<OrderItem>> getOrderItems(String orderId) =>
      (select(orderItems)..where((tbl) => tbl.orderId.equals(orderId))).get();

  Future<void> insertOrderItem(OrderItemsCompanion orderItem) =>
      into(orderItems).insert(orderItem);

  Future<void> insertOrderItems(List<OrderItemsCompanion> orderItemsList) =>
      batch((batch) {
        batch.insertAll(orderItems, orderItemsList);
      });

  Future<void> deleteOrderItems(String orderId) =>
      (delete(orderItems)..where((tbl) => tbl.orderId.equals(orderId))).go();
}