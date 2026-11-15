#pragma once

// A small, asynchronous source/destination sample. Read while the target is still acquired,
// then log the sampled frame on a later begin. No render-thread wait or image file.
struct WorldPixelProbe {
    Microsoft::WRL::ComPtr<ID3D11Texture2D> samples;
    uint64_t frame = 0;
    uint64_t generation = 0;

    bool Queue(ID3D11Device* device, ID3D11DeviceContext* context, ID3D11Texture2D* source,
               ID3D11Texture2D* target, bool destination, uint64_t id, uint64_t gen) {
        if (frame || !source || !target) return false;
        D3D11_TEXTURE2D_DESC sd{};
        source->GetDesc(&sd);
        D3D11_TEXTURE2D_DESC td{};
        target->GetDesc(&td);
        const bool sameFamily = gx_chain::FamilyOf(sd.Format) == gx_chain::FamilyOf(td.Format);
        if (!samples) {
            D3D11_TEXTURE2D_DESC d{};
            d.Width=8; d.Height=4; d.MipLevels=d.ArraySize=1;
            d.Format=gx_chain::FamilyOf(sd.Format)==gx_chain::BGRA8 ?
                DXGI_FORMAT_B8G8R8A8_TYPELESS : DXGI_FORMAT_R8G8B8A8_TYPELESS;
            d.SampleDesc.Count=1; d.Usage=D3D11_USAGE_STAGING; d.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
            if (FAILED(device->CreateTexture2D(&d,nullptr,&samples))) return false;
        }
        for (unsigned row=0;row<4;++row) for(unsigned col=0;col<4;++col) {
            const unsigned x=(2*col+1)*sd.Width/8, y=(2*row+1)*sd.Height/8;
            const D3D11_BOX b={x,y,0,x+1,y+1,1};
            context->CopySubresourceRegion(samples.Get(),0,col,row,0,source,0,&b);
            if(destination&&sameFamily&&td.Width==sd.Width&&td.Height==sd.Height)
                context->CopySubresourceRegion(samples.Get(),0,col+4,row,0,target,0,&b);
        }
        haveDestination=destination&&sameFamily&&td.Width==sd.Width&&td.Height==sd.Height;
        frame=id; generation=gen;
        return true;
    }

    bool Read(ID3D11DeviceContext* context,std::string& result) {
        if(!frame)return false;
        D3D11_MAPPED_SUBRESOURCE map{};
        const HRESULT hr=context->Map(samples.Get(),0,D3D11_MAP_READ,D3D11_MAP_FLAG_DO_NOT_WAIT,&map);
        if(hr==DXGI_ERROR_WAS_STILL_DRAWING)return false;
        result=" frame="+std::to_string(frame)+" generation="+std::to_string(generation);
        frame=0;
        if(FAILED(hr)){result+=" result=unavailable";return true;}
        unsigned sourceRgb=0, targetRgb=0, sourceAlpha=0, targetAlpha=0;
        for(unsigned row=0;row<4;++row){
            const auto* p=static_cast<const uint8_t*>(map.pData)+row*map.RowPitch;
            for(unsigned col=0;col<4;++col){
                const auto* src=p+4*col;
                sourceRgb+=(src[0]|src[1]|src[2])!=0;
                sourceAlpha+=src[3]==255;
                if(haveDestination){
                    const auto* dst=src+16;
                    targetRgb+=(dst[0]|dst[1]|dst[2])!=0;
                    targetAlpha+=dst[3]==255;
                }
            }
        }
        context->Unmap(samples.Get(),0);
        result+=" source_rgb="+std::to_string(sourceRgb)+" source_opaque="+std::to_string(sourceAlpha);
        if(haveDestination)result+=" target_rgb="+std::to_string(targetRgb)+" target_opaque="+std::to_string(targetAlpha);
        return true;
    }
private:
    bool haveDestination = false;
};
