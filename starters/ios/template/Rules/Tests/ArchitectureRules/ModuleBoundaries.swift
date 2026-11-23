import Foundation
import Harmonize
import ModuleShape
import Testing

/// Modules, their dependencies and allowed imports all come from the module shape and Features.swift
/// (Tuist/ProjectDescriptionHelpers). Agents add features and links in Features.swift; only links inside the shape
/// can be written there. A link outside the shape needs the owner: stop and report.
let declared = modules(features, shared: sharedLinks)
let shape = Dictionary(uniqueKeysWithValues: fullShape(features).map { ($0.name, Set($0.dependencies)) })
let projectRoot = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
    .deletingLastPathComponent().deletingLastPathComponent()

@Test func moduleBoundaries() {
    var hits: [String] = []
    for module in declared {
        guard let system = module.systemImports else { continue }
        let allowed = system.union(module.dependencies).union(module.external)
        // Harmonize 1.3.0 matches its skipped folder names (Tests, Fixtures) against paths relative to the scope's
        // base. With .on("Targets/<module>") the base is the module folder itself, so Targets/Fixtures is included here
        // (fail-fixtures-imports-swiftui proves it). Rules scanning all of productionCode() do skip it.
        for source in Harmonize.productionCode().on("Targets/\(module.name)").sources() {
            let file = source.fileName ?? "?"
            for name in Set(source.imports().map(\.name)) where !allowed.contains(name) {
                if shape[module.name, default: []].contains(name) {
                    hits.append("[module-boundaries] \(file) in \(module.name) imports \(name). The module shape allows "
                        + "\(module.name) → \(name), but Features.swift doesn't declare it: add \(linkHint(module.name, name)) "
                        + "in Tuist/ProjectDescriptionHelpers/Features.swift.")
                } else {
                    hits.append("[module-boundaries] \(module.name) may only import: \(allowed.sorted().joined(separator: ", ")). "
                        + "\(file) imports \(name), which is outside the module shape. Move the code to a module allowed "
                        + "to use it, or pass data in through Core or an Interface module. If the link is really needed, "
                        + "stop and report: it needs the owner.")
                }
            }
        }
    }
    #expect(hits.isEmpty, "\(hits.joined(separator: "\n"))")
}

/// Which declaration in Features.swift gives `module` a dependency on `dependency`.
func linkHint(_ module: String, _ dependency: String) -> String {
    for link in SharedLink.allCases
    where modules(features, shared: sharedLinks.union([link])).first(where: { $0.name == module })?.dependencies.contains(dependency) == true {
        return "`.\(link.rawValue)` to sharedLinks"
    }
    for (index, feature) in features.enumerated() {
        for link in FeatureLink.allCases {
            var changed = features
            changed[index] = Feature(feature.name, links: feature.links.union([link]))
            if modules(changed, shared: sharedLinks).first(where: { $0.name == module })?.dependencies.contains(dependency) == true {
                return "`.\(link.rawValue)` to Feature(\"\(feature.name)\")'s links"
            }
        }
    }
    return "the link"
}

/// The generated project has exactly the targets and dependencies the shape gives Features.swift, so a target or
/// dependency hand-edited into Project.swift fails. scripts/check.py writes the dump (`tuist dump project`) first.
@Test func projectFollowsModuleShape() throws {
    let dump = projectRoot.appendingPathComponent(".build/tuist-project.json")
    guard let data = try? Data(contentsOf: dump) else {
        Issue.record("[module-boundaries] No \(dump.path). Run python3 scripts/check.py --only harmonize, which writes it.")
        return
    }
    let project = try JSONDecoder().decode(DumpedProject.self, from: data)
    // Project modules by name, everything else as "<kind> <name>" (external, sdk, framework, package, ...), so a
    // dependency of any other kind, or a package named like a module, never matches.
    let expected = Dictionary(uniqueKeysWithValues: declared.map {
        ($0.name, Set($0.dependencies + $0.external.map { "external \($0)" }))
    })
    var hits: [String] = []
    for target in project.targets {
        guard let want = expected[target.name] else {
            hits.append("[module-boundaries] Project.swift declares target \(target.name), which isn't in the module shape. "
                + "Add a feature in Tuist/ProjectDescriptionHelpers/Features.swift; never edit Project.swift's targets.")
            continue
        }
        let have = Set(target.dependencies.flatMap { $0.map { kind, value in kind == "target" ? value.name ?? "?" : "\(kind) \(value.name ?? "?")" } })
        for extra in have.subtracting(want).sorted() {
            hits.append("[module-boundaries] Project.swift declares \(target.name) → \(extra), which the module shape and "
                + "Features.swift don't give it. Project.swift builds its targets from Features.swift: declare links there "
                + "if the shape allows them, otherwise stop and report. Never hand-edit Project.swift's dependencies.")
        }
        for missing in want.subtracting(have).sorted() {
            hits.append("[module-boundaries] Project.swift is missing \(target.name) → \(missing), which Features.swift "
                + "gives it. Never hand-edit Project.swift's dependencies.")
        }
    }
    for name in Set(expected.keys).subtracting(project.targets.map(\.name)).sorted() {
        hits.append("[module-boundaries] Project.swift has no target \(name), which Features.swift gives it.")
    }
    #expect(hits.isEmpty, "\(hits.joined(separator: "\n"))")
}

/// Every declared module has its folder, and every folder in Targets/ is a declared module.
@Test func featuresMatchFolders() throws {
    var hits: [String] = []
    for feature in features where feature.name.range(of: #"^[A-Z][A-Za-z0-9]*$"#, options: .regularExpression) == nil {
        hits.append("[module-boundaries] Features.swift: \"\(feature.name)\" isn't a valid feature name (UpperCamelCase letters and digits).")
    }
    let names = declared.map(\.name)
    for name in Set(names) where names.filter({ $0 == name }).count > 1 {
        hits.append("[module-boundaries] Features.swift: module \(name) would be declared twice. Pick another feature name.")
    }
    let targets = projectRoot.appendingPathComponent("Targets")
    let folders = Set(try FileManager.default.contentsOfDirectory(atPath: targets.path)
        .filter { var dir: ObjCBool = false; return FileManager.default.fileExists(atPath: targets.appendingPathComponent($0).path, isDirectory: &dir) && dir.boolValue })
    for feature in features {
        let missing = ["\(feature.name)Interface", "\(feature.name)Logic", feature.name, "\(feature.name)Tests"].filter { !folders.contains($0) }
        if !missing.isEmpty {
            hits.append("[module-boundaries] Features.swift declares \(feature.name), but these folders are missing: "
                + "\(missing.map { "Targets/\($0)" }.joined(separator: ", ")). Each feature needs Targets/<Feature>Interface, "
                + "<Feature>Logic, <Feature> and <Feature>Tests.")
        }
    }
    for folder in folders.subtracting(names).sorted() {
        hits.append("[module-boundaries] Targets/\(folder) isn't a module in the shape. Declare its feature in "
            + "Tuist/ProjectDescriptionHelpers/Features.swift, or move the code into an existing module.")
    }
    #expect(hits.isEmpty, "\(hits.joined(separator: "\n"))")
}

/// No folder inside a shipped module is named like a test folder. Harmonize's productionCode() skips folders named
/// *Tests or *Fixtures, so code in Targets/SettingsLogic/NetTests would compile into SettingsLogic while the rules
/// that scan productionCode() never read it.
@Test func noSkippedSubfolders() {
    var hits: [String] = []
    for module in declared where module.role != .tests && module.role != .uiTests {
        let folder = projectRoot.appendingPathComponent("Targets/\(module.name)")
        guard let walker = FileManager.default.enumerator(at: folder, includingPropertiesForKeys: [.isDirectoryKey]) else { continue }
        for case let url as URL in walker
        where (try? url.resourceValues(forKeys: [.isDirectoryKey]).isDirectory) == true
            && (url.lastPathComponent.hasSuffix("Tests") || url.lastPathComponent.hasSuffix("Fixtures")) {
            let components = url.standardizedFileURL.pathComponents
            let path = components[(components.lastIndex(of: "Targets") ?? 0)...].joined(separator: "/")
            hits.append("[module-boundaries] \(path) is inside \(module.name) but named like a test folder. The architecture "
                + "rules skip folders named *Tests or *Fixtures, so they wouldn't check the code in it. Rename the folder; "
                + "tests go in the feature's Tests module.")
        }
    }
    #expect(hits.isEmpty, "\(hits.joined(separator: "\n"))")
}

struct DumpedProject: Decodable {
    struct Target: Decodable {
        /// One key per dependency: its kind (target, external, sdk, ...).
        struct Named: Decodable { let name: String? }
        let name: String
        let dependencies: [[String: Named]]
    }
    let targets: [Target]
}
