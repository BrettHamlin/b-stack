public import Domain
public func label(_ state: SendState) -> String {
    switch state {
    case .draft: "Draft"
    default: "Other"
    }
}
