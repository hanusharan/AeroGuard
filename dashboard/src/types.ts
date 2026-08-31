export interface LeadTimeBucket {
  bucket: string;
  n_positive_rows: number;
  recall: number;
  n_warned: number;
  n_missed: number;
}

export interface WarningCoverage {
  ">=0.5s"?: number;
  ">=1s": number;
  ">=2s": number;
  ">=3s": number;
  ">=4s": number;
  ">=5s": number;
}

export interface Metrics {
  dataset: {
    trajectories: number;
    rows: number;
    trainTrajectories: number;
    valTrajectories: number;
    testTrajectories: number;
    splitOverlap: number;
  };
  v02: {
    prAuc: number;
    eventRecall: number;
    nEvents: number;
    nWarned: number;
    medianLeadTimeS: number;
    warningCoverage: WarningCoverage;
  };
  v03: {
    prAuc: number;
    rocAuc: number;
    precision: number;
    recall: number;
    eventRecall: number;
    nEvents: number;
    nWarned: number;
    medianLeadTimeS: number;
    meanLeadTimeS: number;
    warningCoverage: WarningCoverage;
    leadTimeRecallBuckets: LeadTimeBucket[];
    nFeatures: number;
    windowS: number;
    threshold: number;
  };
  /**
   * Physical precursor: the measured alpha 8°→16° transition time in the
   * dataset itself, independent of any model. Distinct from lead time, which
   * is what the model actually credited.
   */
  precursor: {
    v01MedianS: number;
    v02MedianS: number;
    v03MedianS: number;
    v02Coverage: { ">=2s": number; ">=3s": number };
    v03Coverage: { ">=2s": number; ">=3s": number; ">=4s": number };
  };
  generalization: {
    forward: {
      prAuc: number;
      eventRecall: number;
      nEvents: number;
      nWarned: number;
      medianLeadTimeS: number;
      meanLeadTimeS: number;
      warningCoverage: WarningCoverage;
    };
    reverse: {
      prAuc: number;
      eventRecall: number;
      nEvents: number;
      nWarned: number;
      medianLeadTimeS: number;
      warningCoverage: WarningCoverage;
    };
    decision: string;
    forwardPopulation: {
      n_trajectories: number;
      n_crossing_trajectories: number;
      n_usable_rows: number;
      n_events: number;
    };
    reverseTrainPopulation: {
      n_rows: number;
      n_trajectories: number;
    };
    zeroExposureExclusion: {
      prAuc: number;
      eventRecall: number;
      medianLeadTimeS: number;
    };
  };
  tests: { passing: number; total: number };
}

export interface FlightReplayPoint {
  t: number;
  alphaDeg: number;
  airspeed: number;
  pitchDeg: number;
  pitchRateDeg: number;
  elevatorDeg: number;
  gammaDeg: number;
  stallMarginDeg: number;
  warningProbability: number;
}

export interface FlightReplay {
  trajectoryId: string;
  source: string;
  stallBoundaryDeg: number;
  warningThreshold: number;
  crossingTimeS: number;
  firstWarningTimeS: number;
  creditedLeadTimeS: number;
  points: FlightReplayPoint[];
}
