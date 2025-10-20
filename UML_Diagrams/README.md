# UML Diagrams

This document contains all the UML diagrams for the PLD-AGILE project.

## 📁 Folder Structure

```
UML_Diagrams/
├── README.md                    # This file
├── sprint_diagrams/             # Sprint kanban boards and planning
│   ├── Sprint1.svg
│   ├── Sprint1.pdf
│   ├── Sprint1Code.svg
│   ├── Sprint1Code.pdf
│   ├── Sprint2.svg
│   ├── Sprint2.pdf
│   ├── Sprint3.svg
│   └── Sprint3.pdf
├── plantuml_sources/            # PlantUML source files
│   ├── UC_Diagram.puml
│   ├── data_model_class_diagram.puml
│   ├── parse_map_sequence.puml
│   ├── parse_deliveries_sequence.puml
│   └── P_Diagram.puml
└── documentation/               # Additional documentation
    ├── Glossary_AGILE.pdf
    ├── Use_case_description.pdf
    └── Retrospective_Agile_Team_Photos.docx
```

## Table of Contents
- [Sprint Diagrams](#sprint-diagrams)
- [Use Case Diagram](#use-case-diagram)
- [Class Diagram](#class-diagram)
- [Sequence Diagrams](#sequence-diagrams)
- [Package Diagram](#package-diagram)
- [Additional Documentation](#additional-documentation)

---

## Sprint Diagrams

### Sprint 1
![Sprint 1 Diagram](sprint_diagrams/Sprint1.svg)

[📄 View Sprint 1 PDF](sprint_diagrams/Sprint1.pdf)

### Sprint 1 Code
![Sprint 1 Code Diagram](sprint_diagrams/Sprint1Code.svg)

[📄 View Sprint 1 Code PDF](sprint_diagrams/Sprint1Code.pdf)

### Sprint 2
![Sprint 2 Diagram](sprint_diagrams/Sprint2.svg)

[📄 View Sprint 2 PDF](sprint_diagrams/Sprint2.pdf)

### Sprint 3
![Sprint 3 Diagram](sprint_diagrams/Sprint3.svg)

[📄 View Sprint 3 PDF](sprint_diagrams/Sprint3.pdf)

---

## Use Case Diagram

```plantuml
@startuml
' UC_Diagram.puml content
!include plantuml_sources/UC_Diagram.puml
@enduml
```

[📝 View UC_Diagram.puml source](plantuml_sources/UC_Diagram.puml)

---

## Class Diagram

### Data Model Class Diagram

```plantuml
@startuml
' data_model_class_diagram.puml content
!include plantuml_sources/data_model_class_diagram.puml
@enduml
```

[📝 View data_model_class_diagram.puml source](plantuml_sources/data_model_class_diagram.puml)

---

## Sequence Diagrams

### Parse Map Sequence

```plantuml
@startuml
' parse_map_sequence.puml content
!include plantuml_sources/parse_map_sequence.puml
@enduml
```

[📝 View parse_map_sequence.puml source](plantuml_sources/parse_map_sequence.puml)

### Parse Deliveries Sequence

```plantuml
@startuml
' parse_deliveries_sequence.puml content
!include plantuml_sources/parse_deliveries_sequence.puml
@enduml
```

[📝 View parse_deliveries_sequence.puml source](plantuml_sources/parse_deliveries_sequence.puml)

---

## Package Diagram

```plantuml
@startuml
' P_Diagram.puml content
!include plantuml_sources/P_Diagram.puml
@enduml
```

[📝 View P_Diagram.puml source](plantuml_sources/P_Diagram.puml)

---

## Additional Documentation

### Project Documentation
- 📖 [Glossary (PDF)](documentation/Glossary_AGILE.pdf) - Project terminology and definitions
- 📋 [Use Case Descriptions (PDF)](documentation/Use_case_description.pdf) - Detailed use case specifications
- 📸 [Team Retrospective (DOCX)](documentation/Retrospective_Agile_Team_Photos.docx) - Sprint retrospectives and team reflections

### Sprint Documentation
- 📊 [Sprint 1 PDF](sprint_diagrams/Sprint1.pdf)
- 📊 [Sprint 1 Code PDF](sprint_diagrams/Sprint1Code.pdf)
- 📊 [Sprint 2 PDF](sprint_diagrams/Sprint2.pdf)
- 📊 [Sprint 3 PDF](sprint_diagrams/Sprint3.pdf)

---

## 📝 Notes

- ✅ SVG diagrams are directly embedded and viewable in this markdown file
- ✅ PlantUML diagrams (.puml files) can be rendered using PlantUML tools or IDE plugins
- ✅ PDF documents contain detailed documentation for each sprint and use cases
- ✅ Files are organized into logical folders for easy navigation

## 🔧 Working with PlantUML

### Viewing PlantUML Diagrams

To render PlantUML diagrams, you can use:
- 🌐 [PlantUML Online Server](http://www.plantuml.com/plantuml/uml/)
- 🔌 VS Code extension: "PlantUML" by jebbs
- 💻 Command line: `plantuml *.puml`

### Generating SVG from PlantUML

To generate SVG images from the PlantUML source files:

```bash
cd plantuml_sources
plantuml -tsvg UC_Diagram.puml
plantuml -tsvg data_model_class_diagram.puml
plantuml -tsvg parse_map_sequence.puml
plantuml -tsvg parse_deliveries_sequence.puml
plantuml -tsvg P_Diagram.puml
```

Or generate all diagrams at once:

```bash
cd plantuml_sources
plantuml -tsvg *.puml
```

---

## 📂 Quick Access

| Category | Files |
|----------|-------|
| **Sprint Boards** | [sprint_diagrams/](sprint_diagrams/) |
| **UML Sources** | [plantuml_sources/](plantuml_sources/) |
| **Documentation** | [documentation/](documentation/) |

---

*Last updated: October 20, 2025*
