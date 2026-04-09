import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';
import '../../../domain/entities/settings.dart';
import '../../../domain/usecases/settings/get_settings_usecase.dart';
import '../../../domain/usecases/settings/update_settings_usecase.dart';
import '../../../core/error/failures.dart';

// Events
abstract class SettingsEvent extends Equatable {
  const SettingsEvent();

  @override
  List<Object?> get props => [];
}

class SettingsLoaded extends SettingsEvent {}

class SettingsUpdated extends SettingsEvent {
  final AppSettings settings;

  const SettingsUpdated(this.settings);

  @override
  List<Object?> get props => [settings];
}

class SettingsReset extends SettingsEvent {}

// States
abstract class SettingsState extends Equatable {
  const SettingsState();

  @override
  List<Object?> get props => [];
}

class SettingsInitial extends SettingsState {}

class SettingsLoading extends SettingsState {}

class SettingsLoaded extends SettingsState {
  final AppSettings settings;

  const SettingsLoaded(this.settings);

  @override
  List<Object?> get props => [settings];
}

class SettingsUpdatedSuccess extends SettingsState {
  final AppSettings settings;

  const SettingsUpdatedSuccess(this.settings);

  @override
  List<Object?> get props => [settings];
}

class SettingsError extends SettingsState {
  final String message;

  const SettingsError(this.message);

  @override
  List<Object?> get props => [message];
}

// BLoC
class SettingsBloc extends Bloc<SettingsEvent, SettingsState> {
  final GetSettingsUseCase getSettingsUseCase;
  final UpdateSettingsUseCase updateSettingsUseCase;

  SettingsBloc({
    required this.getSettingsUseCase,
    required this.updateSettingsUseCase,
  }) : super(SettingsInitial()) {
    on<SettingsLoaded>(_onSettingsLoaded);
    on<SettingsUpdated>(_onSettingsUpdated);
    on<SettingsReset>(_onSettingsReset);
  }

  Future<void> _onSettingsLoaded(
    SettingsLoaded event,
    Emitter<SettingsState> emit,
  ) async {
    emit(SettingsLoading());

    final result = await getSettingsUseCase(NoParams());

    result.fold(
      (failure) {
        if (failure is ValidationFailure) {
          emit(SettingsError(failure.errors.isNotEmpty ? failure.errors.first : failure.message));
        } else {
          emit(SettingsError(failure.message));
        }
      },
      (settings) => emit(SettingsLoaded(settings)),
    );
  }

  Future<void> _onSettingsUpdated(
    SettingsUpdated event,
    Emitter<SettingsState> emit,
  ) async {
    emit(SettingsLoading());

    final result = await updateSettingsUseCase(
      UpdateSettingsParams(settings: event.settings),
    );

    result.fold(
      (failure) {
        if (failure is ValidationFailure) {
          emit(SettingsError(failure.errors.isNotEmpty ? failure.errors.first : failure.message));
        } else {
          emit(SettingsError(failure.message));
        }
      },
      (_) => emit(SettingsUpdatedSuccess(event.settings)),
    );
  }

  Future<void> _onSettingsReset(
    SettingsReset event,
    Emitter<SettingsState> emit,
  ) async {
    emit(SettingsLoading());

    final defaultSettings = AppSettings();
    final result = await updateSettingsUseCase(
      UpdateSettingsParams(settings: defaultSettings),
    );

    result.fold(
      (failure) {
        if (failure is ValidationFailure) {
          emit(SettingsError(failure.errors.isNotEmpty ? failure.errors.first : failure.message));
        } else {
          emit(SettingsError(failure.message));
        }
      },
      (_) => emit(SettingsUpdatedSuccess(defaultSettings)),
    );
  }
}