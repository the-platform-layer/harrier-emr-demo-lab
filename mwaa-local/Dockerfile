ARG MWAA_BASE_IMAGE=amazon/mwaa-local:2_10_3
FROM ${MWAA_BASE_IMAGE}

USER root

ENV HARRIER_DEMO_REPO=/usr/local/airflow/harrier-demo-lab

COPY --chown=airflow:airflow mwaa-local/dags /usr/local/airflow/dags
COPY --chown=airflow:airflow mwaa-local/startup_script /usr/local/airflow/startup
COPY --chown=airflow:airflow mwaa-local/scripts /usr/local/airflow/harrier-demo-lab/mwaa-local/scripts
COPY --chown=airflow:airflow scripts /usr/local/airflow/harrier-demo-lab/scripts
COPY --chown=airflow:airflow spark-jobs /usr/local/airflow/harrier-demo-lab/spark-jobs
COPY --chown=airflow:airflow sample-data /usr/local/airflow/harrier-demo-lab/sample-data
COPY --chown=airflow:airflow scenario-configs /usr/local/airflow/harrier-demo-lab/scenario-configs

RUN chmod +x /usr/local/airflow/harrier-demo-lab/mwaa-local/scripts/*.sh \
    /usr/local/airflow/harrier-demo-lab/scripts/*.sh \
    && mkdir -p \
      /usr/local/airflow/harrier-demo-lab/.harrier-demo/runs \
      /usr/local/airflow/harrier-demo-lab/sample-data/generated \
      /usr/local/airflow/harrier-demo-lab/sample-data/large \
    && chown -R airflow:airflow /usr/local/airflow/harrier-demo-lab

USER airflow
