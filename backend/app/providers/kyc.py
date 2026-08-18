import hashlib,hmac,os
class KYC:
    def __init__(self):
        self.base=os.getenv('SUMSUB_BASE_URL','https://api.sumsub.com'); self.app=os.getenv('SUMSUB_APP_TOKEN',''); self.secret=os.getenv('SUMSUB_SECRET_KEY',''); self.level=os.getenv('SUMSUB_LEVEL_NAME','basic-kyc-level')
    def configured(self): return bool(self.app and self.secret)
    def signature(self,timestamp,method,path,body=b''):
        msg=f'{timestamp}{method}{path}'.encode()+body
        return hmac.new(self.secret.encode(),msg,hashlib.sha256).hexdigest()
