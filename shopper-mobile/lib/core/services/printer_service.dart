import 'package:blue_thermal_printer/blue_thermal_printer.dart';
import 'package:flutter/services.dart';

class PrinterService {
  final BlueThermalPrinter _printer = BlueThermalPrinter.instance;

  Future<List<BluetoothDevice>> getDevices() async {
    try {
      return await _printer.getBondedDevices();
    } catch (e) {
      return [];
    }
  }

  Future<bool> connect(BluetoothDevice device) async {
    try {
      final isConnected = await _printer.isConnected;
      if (isConnected == true) return true;
      
      await _printer.connect(device);
      return true;
    } catch (e) {
      return false;
    }
  }

  Future<void> disconnect() async {
    await _printer.disconnect();
  }

  Future<bool> printReceipt(String cleartext) async {
    final isConnected = await _printer.isConnected;
    if (isConnected != true) return false;

    try {
      // Basic text printing for 80mm rollers
      _printer.write(cleartext);
      
      // Feed paper
      _printer.paperCut();
      return true;
    } catch (e) {
      return false;
    }
  }

  Future<bool> get isConnected async => (await _printer.isConnected) ?? false;
}
