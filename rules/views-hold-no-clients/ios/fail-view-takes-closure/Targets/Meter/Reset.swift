public import ComposableArchitecture
public import MeterLogic

extension MeterView {
    public init(store: StoreOf<MeterCounter>, onReset: @escaping @Sendable () -> Void) {
        self.init(store: store)
    }
}
