import subprocess

cmds = [
    [
        "sh",
        "-c",
        "aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 471354727816.dkr.ecr.us-east-1.amazonaws.com"
    ],
    [
        "docker",
        "buildx",
        "build",
        "--platform",
        "linux/amd64",
        "--provenance=false",
        "--load",
        "-f",
        "Dockerfile",
        "-t",
        "str-automation/gform-lambda",
        "."
    ],
    [
        "docker",
        "tag",
        "str-automation/gform-lambda:latest",
        "471354727816.dkr.ecr.us-east-1.amazonaws.com/str-automation/gform-lambda:latest"
    ],
    [
        "docker",
        "push",
        "471354727816.dkr.ecr.us-east-1.amazonaws.com/str-automation/gform-lambda:latest"
    ],
    [
        "aws",
        "lambda",
        "update-function-code",
        "--function-name",
        "str-automation-gform-lambda",
        "--image-uri",
        "471354727816.dkr.ecr.us-east-1.amazonaws.com/str-automation/gform-lambda:latest"
    ]
]

for cmd in cmds:
    subprocess.run(cmd)
