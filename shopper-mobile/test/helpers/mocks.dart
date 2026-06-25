import 'package:mocktail/mocktail.dart';
import 'package:shopper_mobile/data/sources/remote/api_client.dart';
import 'package:shopper_mobile/domain/repositories/product_repository.dart';
import 'package:shopper_mobile/domain/repositories/cart_repository.dart';

class MockApiClient extends Mock implements ApiClient {}
class MockProductRepository extends Mock implements ProductRepository {}
class MockCartRepository extends Mock implements CartRepository {}
