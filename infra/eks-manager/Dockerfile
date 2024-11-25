FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.11

RUN yum update -y && \
    yum install -y gcc python3-devel unzip curl && \
    yum clean all

RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf aws awscliv2.zip

COPY . ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements.txt

# need to update perms on files before building image per:
# https://repost.aws/knowledge-center/lambda-docker-image-error
# chmod 644 *.py requirements.txt
# chmod 755 .
RUN chmod 755 .
RUN chmod 644 ${LAMBDA_TASK_ROOT}/*.py ${LAMBDA_TASK_ROOT}/requirements.txt
#do not use main.py as file name as lambda looks for that by default
CMD [ "index.lambda_handler" ]
