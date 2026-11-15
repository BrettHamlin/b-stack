public import Domain
public func label(_ state: SendState) -> String {
    switch state {
    case .draft: "Draft"
    case .queued: "Queued"
    case .sent: "Sent"
    }
}
