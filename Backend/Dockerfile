# DigiMasterJi Backend - AWS Lambda Container Deployment
# ========================================================
# This Dockerfile creates a Lambda-compatible container image
# using the AWS Lambda Python runtime base image.
#
# Build: docker build -t digimasterji-backend .
# Push:  docker tag digimasterji-backend:latest <account>.dkr.ecr.<region>.amazonaws.com/digimasterji-backend:latest
#        docker push <account>.dkr.ecr.<region>.amazonaws.com/digimasterji-backend:latest

FROM public.ecr.aws/lambda/python:3.11

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy requirements first for better caching
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install Python dependencies
# Use --only-binary :all: to avoid compilation issues (no gcc in Lambda base image)
RUN pip install --no-cache-dir --only-binary :all: -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy application code
COPY app/ ${LAMBDA_TASK_ROOT}/app/

# Fix permissions - Lambda runs as non-root user
RUN chmod -R 755 ${LAMBDA_TASK_ROOT}/app/

# Copy any additional configuration files if needed
COPY .env ${LAMBDA_TASK_ROOT}/.env

# Set the Lambda handler
# The handler is: app.main.handler (Mangum wraps the FastAPI app)
CMD ["app.main.handler"]
