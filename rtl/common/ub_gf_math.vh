// GF(2^8) math functions for UB Controller
// Primitive polynomial: x^8 + x^4 + x^3 + x^2 + 1 (0x11D)

function automatic [7:0] gf_mul;
    input [7:0] a;
    input [7:0] b;
    reg [7:0] p;
    integer i;
    begin
        p = 0;
        for (i = 0; i < 8; i = i + 1) begin
            if (b[i])
                p = p ^ a;
            if (a[7])
                a = (a << 1) ^ 8'h1D;
            else
                a = a << 1;
        end
        gf_mul = p;
    end
endfunction

// Multiplication by constant can be optimized, but for now we use the general function.

function automatic [7:0] gf_inv;
    input [7:0] a;
    reg [7:0] p;
    reg [7:0] a_pow;
    begin
        // Inversion in GF(2^8) can be done by a^{254}
        // 254 = 128 + 64 + 32 + 16 + 8 + 4 + 2
        p = 8'h01;
        a_pow = a;
        // a^2
        a_pow = gf_mul(a_pow, a_pow);
        p = gf_mul(p, a_pow); // p = a^2
        // a^4
        a_pow = gf_mul(a_pow, a_pow);
        p = gf_mul(p, a_pow); // p = a^6
        // a^8
        a_pow = gf_mul(a_pow, a_pow);
        p = gf_mul(p, a_pow); // p = a^14
        // a^16
        a_pow = gf_mul(a_pow, a_pow);
        p = gf_mul(p, a_pow); // p = a^30
        // a^32
        a_pow = gf_mul(a_pow, a_pow);
        p = gf_mul(p, a_pow); // p = a^62
        // a^64
        a_pow = gf_mul(a_pow, a_pow);
        p = gf_mul(p, a_pow); // p = a^126
        // a^128
        a_pow = gf_mul(a_pow, a_pow);
        p = gf_mul(p, a_pow); // p = a^254
        gf_inv = p;
    end
endfunction
