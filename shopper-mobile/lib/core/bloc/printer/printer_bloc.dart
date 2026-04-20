import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';
import 'package:blue_thermal_printer/blue_thermal_printer.dart';
import '../../services/printer_service.dart';

// Events
abstract class PrinterEvent extends Equatable {
  const PrinterEvent();
  @override
  List<Object?> get props => [];
}

class PrinterScanRequested extends PrinterEvent {}

class PrinterConnectRequested extends PrinterEvent {
  final BluetoothDevice device;
  const PrinterConnectRequested(this.device);
  @override
  List<Object?> get props => [device];
}

class PrinterDisconnectRequested extends PrinterEvent {}

class PrinterTestPrintRequested extends PrinterEvent {}

// States
abstract class PrinterState extends Equatable {
  const PrinterState();
  @override
  List<Object?> get props => [];
}

class PrinterInitial extends PrinterState {}

class PrinterScanning extends PrinterState {}

class PrinterScanSuccess extends PrinterState {
  final List<BluetoothDevice> devices;
  const PrinterScanSuccess(this.devices);
  @override
  List<Object?> get props => [devices];
}

class PrinterConnecting extends PrinterState {}

class PrinterConnected extends PrinterState {
  final BluetoothDevice device;
  const PrinterConnected(this.device);
  @override
  List<Object?> get props => [device];
}

class PrinterDisconnected extends PrinterState {}

class PrinterError extends PrinterState {
  final String message;
  const PrinterError(this.message);
  @override
  List<Object?> get props => [message];
}

// BLoC
class PrinterBloc extends Bloc<PrinterEvent, PrinterState> {
  final PrinterService printerService;

  PrinterBloc(this.printerService) : super(PrinterInitial()) {
    on<PrinterScanRequested>(_onScanRequested);
    on<PrinterConnectRequested>(_onConnectRequested);
    on<PrinterDisconnectRequested>(_onDisconnectRequested);
    on<PrinterTestPrintRequested>(_onTestPrintRequested);
  }

  Future<void> _onScanRequested(PrinterScanRequested event, Emitter<PrinterState> emit) async {
    emit(PrinterScanning());
    final devices = await printerService.getDevices();
    emit(PrinterScanSuccess(devices));
  }

  Future<void> _onConnectRequested(PrinterConnectRequested event, Emitter<PrinterState> emit) async {
    emit(PrinterConnecting());
    final success = await printerService.connect(event.device);
    if (success) {
      emit(PrinterConnected(event.device));
    } else {
      emit(const PrinterError('Failed to connect to printer'));
    }
  }

  Future<void> _onDisconnectRequested(PrinterDisconnectRequested event, Emitter<PrinterState> emit) async {
    await printerService.disconnect();
    emit(PrinterDisconnected());
  }

  Future<void> _onTestPrintRequested(PrinterTestPrintRequested event, Emitter<PrinterState> emit) async {
    final success = await printerService.printReceipt('SHOOPER POS\n--- TEST PRINT ---\n\n\n');
    if (!success) {
      emit(const PrinterError('Failed to print receipt'));
    }
  }
}
