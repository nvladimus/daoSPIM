def get_params_as_text(run_settings, metric_settings, simulation_settings):
    """Collect important parameters as text string for saving"""
    txt = 'Run params:\n'
    for field in run_settings._fields:
        txt += f"{field}: {getattr(run_settings, field)}\n"

    txt += '\nMetric params:\n'
    # metric-specific params
    for field in metric_settings._fields:
        txt += f"{field}: {getattr(metric_settings, field)}\n"

    return txt