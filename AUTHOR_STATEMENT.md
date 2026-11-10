# Author Statement

**Project:** AeroGuard — Physics-Informed Machine Learning for Early Aircraft Stall Warning  
**Author:** Bulusu Hanu Sharan  
**Repository:** https://github.com/hanusharan/AeroGuard  
**Research DOI:** https://doi.org/10.5281/zenodo.22724022

## 1. Origin and motivation

AeroGuard began with my longstanding interest in aviation and aircraft. My uncle, who has worked in the aeronautical sector, and I often talk about aircraft and aviation engineering. In one of these conversations, he introduced me to the problem of aerodynamic stalls. I became particularly interested in whether artificial intelligence and machine learning could help identify an approaching stall before it occurs.

That curiosity developed into the research question behind AeroGuard: whether a machine-learning model, working with information from a simplified flight-dynamics simulation, could identify physically meaningful precursors to an aerodynamic stall and provide an earlier warning than a model relying only on instantaneous aircraft-state information.

My uncle encouraged me throughout the project and suggested that I consider publishing the work. Our discussions helped sustain my interest in the aviation problem. The research direction and experimental decisions described below were my own.

My longer-term ambition is to investigate whether this line of work could eventually contribute to software for aircraft. I understand that moving from a simplified simulation to any real-aircraft application would require substantially more evidence, realistic aircraft models, independent validation and appropriate aviation safety and certification processes. AeroGuard is not a validated or flight-certified aircraft system.

## 2. My intellectual and research contributions

I conceived the research direction and was responsible for the central hypotheses and principal experimental decisions. These included:

- Selecting early stall warning, rather than only post-event stall detection, as the problem to investigate.
- Defining the research questions and hypotheses.
- Directing the design of the simulator around the physical behaviour I wanted to investigate.
- Determining the experimental direction and the iterations needed to investigate the research hypotheses.
- Directing dataset and model development, including the comparison between instantaneous and temporal approaches.
- Deciding to investigate whether predictive performance transferred across structurally different control-input mechanisms, rather than relying only on performance within the training distribution.
- Reviewing the reported machine-learning results, discussing interpretations and considering what further experiments or corrections were needed.

The project's transition through successive dataset and experiment versions was part of this investigation. In particular, the v0.3 work examined whether a longer physical precursor could be represented in the simulated data and whether a temporal model's warning performance would transfer to a structurally different control-input mechanism.

The research question, hypotheses, intended simulator behaviour and principal experimental choices were mine. AI-assisted tools supported parts of the software implementation and review workflow, as explained below.

## 3. Technical development and implementation

AeroGuard combines a simplified two-dimensional longitudinal flight-dynamics simulator, trajectory-dataset generation, feature and label construction, machine-learning pipelines, baseline comparisons and evaluation procedures.

I communicated the simulator's intended behaviour, research requirements and implementation specifications to Claude Code. I used it as an AI-assisted software-development tool to help translate those specifications into code. I directed the development through iterative instructions, shared my reasoning and requested changes where the implementation did not match the intended design.

I also used Claude Code to help develop the project's website and to support examination and discussion of machine-learning results. I reviewed results with the tool, shared my interpretations and asked it to identify possible errors or weaknesses. AI-generated suggestions were inputs to my evaluation; they were not treated as independent scientific confirmation.

This statement distinguishes my responsibility for the research conception, hypotheses, experimental direction and design decisions from the AI-assisted implementation work. It does not claim that every line of code was written manually by me.

## 4. Use of AI assistance

Claude Code was used as an AI-assisted software-development and research-support tool. Its uses included:

1. **Simulator and research-pipeline implementation:** Helping translate the requirements and intended behaviour I specified into software.
2. **Iterative development:** Implementing requested refinements and corrections as I evaluated the system against the research goals.
3. **Results discussion:** Helping inspect and discuss trained-model results and possible interpretations. I shared my own reasoning and asked the tool to challenge or correct it where appropriate.
4. **Website development:** Assisting with the design and implementation of the AeroGuard website.

I supplied the research direction, hypotheses, requirements and principal experimental decisions. I remain responsible for the scientific claims made in the paper and for ensuring that the code, methods, results and interpretations can withstand independent scrutiny.

AI-generated code, analysis and explanations can contain errors. Their use does not constitute independent validation. Claims in the research should therefore be supported by documented methods, reproducible experiments and scrutiny by qualified researchers.

## 5. Research integrity, reporting and limitations

I consider transparency especially important because AeroGuard addresses a problem connected to aviation safety. The project documentation is intended to preserve the research process, including experimental configurations, dataset versions, methodological changes, historical results, rejected alternatives and reproducibility information.

The results must be interpreted within the limits of the study:

- The simulator is a simplified educational two-dimensional longitudinal model. It is not a validated representation of any particular real aircraft.
- The reported model performance is simulation-based and does not demonstrate performance on real aircraft or establish operational safety.
- The reported event-level metrics apply to a defined evaluated population. The project documentation identifies test-set stall crossings that fall outside the evaluated prediction rows because they occur near the end of a trajectory, beyond the complete future-label window. These crossings are not counted as either warned or missed in the reported event recall. This exclusion and its possible effect on interpretation must remain visible to readers and should receive independent methodological scrutiny.
- Transfer across the tested control-input mechanisms does not establish universal generalization across arbitrary unseen flight regimes.
- Further independent assessment is needed, including examination of the simulator assumptions, event definitions, evaluation protocol, statistical analysis, data handling and reproducibility.

I will not present simulation results as evidence of real-world aircraft readiness. I welcome critical review, attempts to reproduce the work and identification of weaknesses. Any corrections or additional claims should be supported by transparent evidence and documented changes rather than by selectively presenting favourable results.

## 6. Acknowledgements

I am grateful to my uncle for sharing his professional perspective on the aeronautical sector, discussing aviation and aircraft with me, encouraging my interest in aerodynamic stalls, supporting me throughout the research process and suggesting that I pursue publication.

I acknowledge Claude Code as an AI-assisted software-development and research-support tool used in the manner described in this statement.

## 7. Researcher's perspective

AeroGuard grew from a personal interest in aviation into an attempt to investigate a specific engineering and safety-related problem through simulation and machine learning. The process has required me to think about more than model performance: it has involved forming hypotheses, specifying a physical system, designing experiments, interpreting results and recognizing where the available evidence is insufficient.

I see the current work as an initial research contribution, not a final solution to aircraft stall prediction. My next objective is to subject the methods and findings to independent review by aerospace and machine-learning researchers, address valid criticisms and understand what further evidence would be required before the work could be extended towards more realistic applications.

I welcome methodological disagreement and independent reproduction. I regard these as essential parts of responsible scientific work.

---

**Author:** Bulusu Hanu Sharan  
**Date:** [Author to insert the date of final review and approval]

**Declaration:** I have reviewed this statement and confirm that it accurately describes my contributions, the support I received and the use of AI-assisted tools to the best of my knowledge.
